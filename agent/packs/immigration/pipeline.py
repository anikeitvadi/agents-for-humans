"""Ties the immigration pack together: deterministic rule -> engine
(gate + persistence) -> attorney draft, only when the gate surfaces.
No LLM call is required for the discrepancy check itself; drafting will
use a Strands Agent when one is supplied (see agent/llm/draft.py), and
falls back to the deterministic core otherwise.
"""

import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from strands import Agent

from agent.config import RULE_VERSION
from agent.engine.engine import RuleOutcome, ensure_draft, process_event
from agent.engine.schema import Alert, Clock, Event
from agent.engine.store import Store
from agent.llm.draft import DraftResult, build_attorney_draft
from agent.llm.extract import extract_fields
from agent.packs.immigration.rules import check_i94_i797_discrepancy

SAMPLE_CASE_NAME = "Sample Case — H-1B, I-94 cut to passport expiry"
SPECIMENS_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "sample_case" / "specimens"

# (specimen document key, field extracted from it) — one field per document,
# matching agent/llm/document_client.py's recorded-response fixture keys.
_SAMPLE_CASE_DOCUMENTS = [
    ("i94", "admit_until"),
    ("i797", "i797_valid_until"),
    ("passport", "passport_expiry"),
]


def _validate_png(document_bytes: bytes) -> str | None:
    """Actually decodes the bytes as a PNG (not just a magic-byte check) so a
    truncated-but-signature-valid file is rejected before any model call
    (F3). Returns an error string, or None if the bytes are a real PNG."""
    if not document_bytes:
        return "empty file"
    try:
        with Image.open(io.BytesIO(document_bytes), formats=["PNG"]) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return f"not a valid PNG image: {exc}"
    return None


def _sha256(document_bytes: bytes) -> str:
    return hashlib.sha256(document_bytes).hexdigest()


def _known_specimen_hashes() -> dict[str, str]:
    return {key: _sha256((SPECIMENS_DIR / f"{key}.png").read_bytes()) for key, _ in _SAMPLE_CASE_DOCUMENTS}


@dataclass
class SampleCaseExtraction:
    fields: dict[str, str | None] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    statuses: dict[str, str] = field(default_factory=dict)
    needs_review: bool = False
    mode: str = "recorded"
    mode_reason: str | None = None
    # sha256 of each uploaded document's bytes — the document *identity*,
    # independent of what fields the model happened to read from it. Used
    # both to verify a recorded-mode replay is tied to a known specimen (F2)
    # and to key the persisted result so two different document sets that
    # happen to extract the same dates are never treated as the same case
    # (see _derive_event_id below).
    provenance: dict[str, str] = field(default_factory=dict)


def extract_case_documents(client, mode: str, model_id: str, documents: dict[str, bytes]) -> SampleCaseExtraction:
    """Runs the real extract_fields() validation logic against caller-
    supplied document bytes — an actual upload's selected bytes, or (via
    extract_sample_case_fields below) the bundled specimen files — via
    either a live Bedrock client or a recorded-response replay
    (agent/llm/document_client.py). The caller-supplied `mode` label must be
    surfaced wherever this result is shown (C1). This is the single
    extraction pass whose evidence and decision must never diverge (R2) —
    callers must not extract twice for one case.

    Every document is validated as a real, decodable PNG before any model
    call (F3). If the final client mode ends up "recorded" (whether it
    started that way or failed over mid-batch), every document's bytes must
    match a known bundled specimen (F2) — an offline replay must never
    accept arbitrary or swapped files as if they were the known sample. A
    client that starts live and fails over partway through a batch must not
    silently combine a genuine live result with recorded ones (see
    FailoverExtractionClient's docstring) — that condition is treated the
    same as an unverified recorded batch: a controlled review state, not a
    mixed-provenance result.
    """
    provenance = {key: _sha256(documents[key]) for key, _ in _SAMPLE_CASE_DOCUMENTS}

    for document_key, _ in _SAMPLE_CASE_DOCUMENTS:
        error = _validate_png(documents[document_key])
        if error is not None:
            return SampleCaseExtraction(
                needs_review=True,
                mode=mode,
                mode_reason=f"document '{document_key}' rejected before any model call: {error}",
                provenance=provenance,
            )

    extraction = SampleCaseExtraction(mode=mode, provenance=provenance)
    modes_seen: list[str] = []
    first_field_error: str | None = None

    for document_key, field_name in _SAMPLE_CASE_DOCUMENTS:
        document_bytes = documents[document_key]
        result = extract_fields(
            client,
            document_bytes=document_bytes,
            document_format="png",
            field_names=[field_name],
            model_id=model_id,
            document_name=document_key,
            date_fields=[field_name],
        )
        modes_seen.append(getattr(client, "mode", mode))
        if result.error is not None and first_field_error is None:
            # A raw client (not wrapped in FailoverExtractionClient) that
            # raises directly to extract_fields — e.g. an account-blocked
            # error — must have that message surfaced, not replaced by a
            # generic "needs review" string.
            first_field_error = result.error

        field_result = result.fields.get(field_name)
        if field_result is None:
            extraction.fields[field_name] = None
            extraction.evidence[field_name] = ""
            extraction.statuses[field_name] = "missing"
            extraction.needs_review = True
            continue

        extraction.fields[field_name] = field_result.value
        extraction.evidence[field_name] = field_result.evidence
        extraction.statuses[field_name] = field_result.status
        if result.needs_review:
            extraction.needs_review = True

    # A client that flips mode between calls has already mixed a genuine
    # live result with recorded ones — no final label can make that
    # coherent, so refuse the whole batch rather than present it as either.
    if len(set(modes_seen)) > 1:
        return SampleCaseExtraction(
            needs_review=True,
            mode="recorded",
            mode_reason=(
                "live Bedrock extraction failed partway through this upload; refusing to combine "
                "live and recorded fields into one result"
            ),
            provenance=provenance,
        )

    final_mode = modes_seen[0] if modes_seen else mode
    extraction.mode = final_mode
    # A failover client's truthful fallback_reason (it already produced a
    # usable recorded result) takes precedence when both are present; a raw
    # client's outright request failure is the only explanation otherwise.
    extraction.mode_reason = getattr(client, "fallback_reason", None) or first_field_error

    if final_mode == "recorded":
        known = _known_specimen_hashes()
        if any(provenance[key] != known[key] for key, _ in _SAMPLE_CASE_DOCUMENTS):
            return SampleCaseExtraction(
                needs_review=True,
                mode="recorded",
                mode_reason=(
                    "this offline demo's recorded mode only replays results for the bundled synthetic "
                    "sample documents — these uploaded files don't match them"
                ),
                provenance=provenance,
            )

    return extraction


def extract_sample_case_fields(client, mode: str, model_id: str) -> SampleCaseExtraction:
    """Convenience wrapper over extract_case_documents() using the bundled
    specimen files — kept for tests/tooling that want the fixture bytes
    without an upload. The real app path (run_case_from_documents) takes
    caller-supplied bytes directly."""
    documents = {key: (SPECIMENS_DIR / f"{key}.png").read_bytes() for key, _ in _SAMPLE_CASE_DOCUMENTS}
    return extract_case_documents(client, mode=mode, model_id=model_id, documents=documents)


@dataclass
class SampleCaseResult:
    alert: Alert | None
    draft: DraftResult | None
    extraction: SampleCaseExtraction
    error: str | None = None
    # {clock_id, event_id, rule_version} the draft/alert/receipt are keyed
    # under — the caller (agent/app.py) must use this, not a hand-rolled
    # fixed id, so a different submission never inherits another one's draft
    # or approval (F1).
    ref: dict[str, str] | None = None


def _derive_event_id(extraction: SampleCaseExtraction, rule_version: str) -> str:
    """Identity of a submission = its complete immutable result: which
    documents were uploaded (provenance), what was read from them (fields/
    evidence/statuses), and how (mode/mode_reason) — not just the extracted
    dates. Two different document sets that happen to extract the same
    dates must not collide (that would let a new upload inherit an old
    draft and its approval receipt); a hash of dates alone cannot tell them
    apart, but their evidence and document provenance differ."""
    canonical = json.dumps(
        {
            "fields": extraction.fields,
            "evidence": extraction.evidence,
            "statuses": extraction.statuses,
            "mode": extraction.mode,
            "mode_reason": extraction.mode_reason,
            "provenance": extraction.provenance,
            "rule_version": rule_version,
        },
        sort_keys=True,
    )
    return "doc-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def run_case_from_documents(
    store: Store,
    clock_id: str,
    client,
    mode: str,
    model_id: str,
    documents: dict[str, bytes],
    agent: Agent | None = None,
    expected_epoch: int | None = None,
) -> SampleCaseResult:
    """Extracts caller-supplied document bytes once, then runs the
    discrepancy check only if every critical field extracted cleanly — an
    extraction result that needs review must block the rule rather than
    feed a null/ambiguous value into date arithmetic (F4's contract applies
    upstream of the rule too). The returned extraction is exactly what the
    decision/draft were computed from — no second extraction call (R2).

    The event identity is derived from the complete extraction result
    (_derive_event_id), not supplied by the caller — that is what keeps a
    changed submission from ever retrieving another submission's draft or
    approval (F1), while an identical replay of the same documents/result
    deterministically retrieves the same draft. The complete result (fields,
    evidence, statuses, mode, provenance) is persisted under that identity
    via the event payload's "_result" key so a later replay, the guardian,
    or an approval can refer to the exact artifact a person reviewed (see
    get_persisted_result).
    """
    extraction = extract_case_documents(client, mode=mode, model_id=model_id, documents=documents)

    if extraction.needs_review:
        return SampleCaseResult(
            alert=None,
            draft=None,
            extraction=extraction,
            error=extraction.mode_reason or "Document extraction needs review before the discrepancy check can run.",
        )

    event_id = _derive_event_id(extraction, RULE_VERSION)
    ref = {"clock_id": clock_id, "event_id": event_id, "rule_version": RULE_VERSION}
    fields = {
        **extraction.fields,
        "case_name": SAMPLE_CASE_NAME,
        "_result": {
            "fields": extraction.fields,
            "evidence": extraction.evidence,
            "statuses": extraction.statuses,
            "needs_review": extraction.needs_review,
            "mode": extraction.mode,
            "mode_reason": extraction.mode_reason,
            "provenance": extraction.provenance,
        },
    }
    result = run_discrepancy_check(
        store, clock_id=clock_id, event_id=event_id, fields=fields, agent=agent, expected_epoch=expected_epoch
    )
    return SampleCaseResult(alert=result.alert, draft=result.draft, extraction=extraction, error=None, ref=ref)


def run_sample_case(
    store: Store,
    clock_id: str,
    client,
    mode: str,
    model_id: str,
    agent: Agent | None = None,
    expected_epoch: int | None = None,
) -> SampleCaseResult:
    """Convenience wrapper over run_case_from_documents() using the bundled
    specimen files."""
    documents = {key: (SPECIMENS_DIR / f"{key}.png").read_bytes() for key, _ in _SAMPLE_CASE_DOCUMENTS}
    return run_case_from_documents(store, clock_id, client, mode, model_id, documents, agent=agent, expected_epoch=expected_epoch)


def get_persisted_result(store: Store, ref: dict[str, str]) -> SampleCaseExtraction | None:
    """Reconstructs the exact immutable extraction result an earlier
    run_case_from_documents() call persisted, from its event payload — so a
    replay, the guardian, or an approval can refer to the precise artifact
    a person reviewed (evidence included), not re-derive it. Returns None if
    no event is stored under this ref (e.g. it was cleared by a reset)."""
    event = store.get_event(ref["event_id"])
    if event is None or event.payload.get("_result") is None:
        return None
    payload = event.payload["_result"]
    return SampleCaseExtraction(
        fields=payload["fields"],
        evidence=payload["evidence"],
        statuses=payload["statuses"],
        needs_review=payload["needs_review"],
        mode=payload["mode"],
        mode_reason=payload["mode_reason"],
        provenance=payload["provenance"],
    )


@dataclass
class PipelineResult:
    alert: Alert
    draft: DraftResult | None


def run_discrepancy_check(
    store: Store,
    clock_id: str,
    event_id: str,
    fields: dict,
    agent: Agent | None = None,
    expected_epoch: int | None = None,
) -> PipelineResult:
    discrepancy = check_i94_i797_discrepancy(
        i94_admit_until=fields["admit_until"], i797_valid_until=fields["i797_valid_until"]
    )

    clock = Clock(clock_id=clock_id, user_id="demo-user", module="immigration", rule_id="i94_i797_discrepancy", state="quiet")
    event = Event(
        event_id=event_id, source="document_upload", effective_date=fields["admit_until"], rule_version=RULE_VERSION, payload=fields
    )
    outcome = RuleOutcome(material=discrepancy.discrepant, actionable=discrepancy.discrepant, window_open=discrepancy.discrepant)

    alert = process_event(store, clock, event, outcome, expected_epoch=expected_epoch)

    # Whether a draft should exist is decided by the rule outcome, not by
    # alert.decision — a discrepant case must end up with a ready draft
    # whether this is the first surfacing, a routine silent replay, or
    # recovery from a crash that persisted the surfaced alert but never
    # reached the draft-save step (R4).
    draft = ensure_draft(
        store,
        clock,
        event,
        should_have_draft=discrepancy.discrepant,
        build_draft=lambda: build_attorney_draft(
            rule_message=discrepancy.message,
            subject_facts={"case_name": fields.get("case_name", "immigration documents")},
            agent=agent,
        ),
        expected_epoch=expected_epoch,
    )

    return PipelineResult(alert=alert, draft=draft)
