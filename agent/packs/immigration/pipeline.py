"""Ties the immigration pack together: deterministic rule -> engine
(gate + persistence) -> attorney draft, only when the gate surfaces.
No LLM call is required for the discrepancy check itself; drafting will
use a Strands Agent when one is supplied (see agent/llm/draft.py), and
falls back to the deterministic core otherwise.
"""

from dataclasses import dataclass, field
from pathlib import Path

from strands import Agent

from agent.engine.engine import RuleOutcome, process_event
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


@dataclass
class SampleCaseExtraction:
    fields: dict[str, str | None] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    statuses: dict[str, str] = field(default_factory=dict)
    needs_review: bool = False
    mode: str = "recorded"


def extract_sample_case_fields(client, mode: str, model_id: str) -> SampleCaseExtraction:
    """Runs the real extract_fields() validation logic against each sample
    specimen image, via either a live Bedrock client or a recorded-response
    replay (agent/llm/document_client.py) — the caller-supplied `mode` label
    must be surfaced wherever this result is shown (C1)."""
    extraction = SampleCaseExtraction(mode=mode)

    for document_key, field_name in _SAMPLE_CASE_DOCUMENTS:
        document_bytes = (SPECIMENS_DIR / f"{document_key}.png").read_bytes()
        result = extract_fields(
            client,
            document_bytes=document_bytes,
            document_format="png",
            field_names=[field_name],
            model_id=model_id,
            document_name=document_key,
        )
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

    return extraction


@dataclass
class SampleCaseResult:
    alert: Alert | None
    draft: DraftResult | None
    extraction: SampleCaseExtraction
    error: str | None = None


def run_sample_case(
    store: Store,
    clock_id: str,
    event_id: str,
    client,
    mode: str,
    model_id: str,
    agent: Agent | None = None,
) -> SampleCaseResult:
    """Extracts the sample case's three specimen documents, then runs the
    discrepancy check only if every critical field extracted cleanly — an
    extraction result that needs review must block the rule rather than
    feed a null/ambiguous value into date arithmetic (F4's contract applies
    upstream of the rule too)."""
    extraction = extract_sample_case_fields(client, mode=mode, model_id=model_id)

    if extraction.needs_review:
        return SampleCaseResult(
            alert=None,
            draft=None,
            extraction=extraction,
            error="Document extraction needs review before the discrepancy check can run.",
        )

    fields = {**extraction.fields, "case_name": SAMPLE_CASE_NAME}
    result = run_discrepancy_check(store, clock_id=clock_id, event_id=event_id, fields=fields, agent=agent)
    return SampleCaseResult(alert=result.alert, draft=result.draft, extraction=extraction, error=None)


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
) -> PipelineResult:
    discrepancy = check_i94_i797_discrepancy(
        i94_admit_until=fields["admit_until"], i797_valid_until=fields["i797_valid_until"]
    )

    clock = Clock(clock_id=clock_id, user_id="demo-user", module="immigration", rule_id="i94_i797_discrepancy", state="quiet")
    event = Event(event_id=event_id, source="document_upload", effective_date=fields["admit_until"], rule_version="v1", payload=fields)
    outcome = RuleOutcome(material=discrepancy.discrepant, actionable=discrepancy.discrepant, window_open=discrepancy.discrepant)

    alert = process_event(store, clock, event, outcome)

    draft = None
    if alert.decision == "surfaced":
        # First (and only) claim of this alert — F3 guarantees a later
        # repeat call gets "silent" instead, so this always builds a new
        # draft, never a duplicate. Persist it so it survives a page
        # reload or process restart (C2) instead of existing only in this
        # one response.
        draft = build_attorney_draft(
            rule_message=discrepancy.message,
            subject_facts={"case_name": fields.get("case_name", "immigration documents")},
            agent=agent,
        )
        store.save_draft(
            clock_id=clock.clock_id,
            event_id=event.event_id,
            rule_version=event.rule_version,
            status="ready",
            subject=draft.subject,
            body=draft.body,
            used_llm_personalization=draft.used_llm_personalization,
        )
    else:
        # No new ping, but a prior surfaced alert may have left an
        # unresolved draft — retrieve it rather than silently dropping
        # access to it (C2's "reload/restart retrieves the original draft").
        existing = store.get_draft(clock_id=clock.clock_id, event_id=event.event_id, rule_version=event.rule_version)
        if existing is not None and existing.status == "ready":
            draft = DraftResult(
                subject=existing.subject,
                body=existing.body,
                used_llm_personalization=bool(existing.used_llm_personalization),
            )

    return PipelineResult(alert=alert, draft=draft)
