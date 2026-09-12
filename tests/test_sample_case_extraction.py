from agent.engine.store import Store
from agent.llm.document_client import RecordedResponseClient
from agent.packs.immigration.pipeline import (
    SPECIMENS_DIR,
    extract_case_documents,
    extract_sample_case_fields,
    get_persisted_result,
    run_case_from_documents,
    run_sample_case,
)


def _specimen_bytes():
    return {
        "i94": (SPECIMENS_DIR / "i94.png").read_bytes(),
        "i797": (SPECIMENS_DIR / "i797.png").read_bytes(),
        "passport": (SPECIMENS_DIR / "passport.png").read_bytes(),
    }


def test_extract_sample_case_fields_returns_all_three_fields_with_evidence():
    extraction = extract_sample_case_fields(RecordedResponseClient(), mode="recorded", model_id="fake-model-id")

    assert extraction.fields["admit_until"] == "2026-11-03"
    assert extraction.fields["i797_valid_until"] == "2026-12-28"
    assert extraction.fields["passport_expiry"] == "2026-11-03"
    assert extraction.evidence["admit_until"] == "Admit Until Date: 11/03/2026"
    assert extraction.needs_review is False
    assert extraction.mode == "recorded"


def test_extract_sample_case_fields_flags_needs_review_on_missing_document_response():
    client = RecordedResponseClient(responses={"i94": {}, "i797": {}, "passport": {}})

    extraction = extract_sample_case_fields(client, mode="recorded", model_id="fake-model-id")

    assert extraction.needs_review is True
    assert extraction.statuses["admit_until"] == "missing"


def test_run_sample_case_surfaces_discrepancy_end_to_end(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_sample_case(store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id")

    assert result.error is None
    assert result.alert.decision == "surfaced"
    assert result.draft is not None
    assert "55" in result.draft.body
    assert result.extraction.mode == "recorded"
    assert result.ref["clock_id"] == "c1"


def test_run_sample_case_draft_survives_repeat_call_and_restart(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))

    first = run_sample_case(store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id")

    restarted_store = Store(str(db_path))
    replayed = run_sample_case(
        restarted_store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id"
    )

    assert replayed.alert.decision == "silent"
    assert replayed.draft is not None
    assert replayed.draft.body == first.draft.body
    assert replayed.ref == first.ref


def test_run_sample_case_does_not_run_the_rule_when_extraction_needs_review(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    client = RecordedResponseClient(responses={"i94": {}, "i797": {}, "passport": {}})

    result = run_sample_case(store, clock_id="c1", client=client, mode="recorded", model_id="fake-model-id")

    assert result.error is not None
    assert result.alert is None
    assert result.draft is None
    assert result.ref is None


class _RaisingClient:
    """Stands in for a Bedrock client whose Converse call fails outright
    (account block, network, throttling) rather than returning bad JSON."""

    def converse(self, **kwargs):
        raise RuntimeError("Error 002: Access to Bedrock models is not allowed for this account")


def test_extraction_api_failure_is_a_visible_error_not_a_crash(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_sample_case(store, clock_id="c1", client=_RaisingClient(), mode="live", model_id="m")

    assert result.alert is None
    assert result.draft is None
    assert result.extraction.mode == "live"
    assert result.extraction.needs_review is True
    assert "Error 002" in result.error


def test_extract_case_documents_runs_against_caller_supplied_bytes_not_the_fixture_path():
    # R2: the caller's actually-selected bytes must be what gets extracted —
    # not a second, independent read of the specimen files.
    extraction = extract_case_documents(
        RecordedResponseClient(), mode="recorded", model_id="fake-model-id", documents=_specimen_bytes()
    )

    assert extraction.fields["admit_until"] == "2026-11-03"
    assert extraction.fields["i797_valid_until"] == "2026-12-28"
    assert extraction.needs_review is False


def test_run_case_from_documents_returns_evidence_bound_to_the_same_extraction_that_produced_the_decision(tmp_path):
    # R2: one extraction produces both the evidence shown and the decision/
    # draft — never two independent extraction calls that could disagree.
    store = Store(str(tmp_path / "ledger.db"))

    result = run_case_from_documents(
        store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id", documents=_specimen_bytes()
    )

    assert result.error is None
    assert result.extraction.fields["admit_until"] == "2026-11-03"
    assert result.extraction.evidence["admit_until"] == "Admit Until Date: 11/03/2026"
    assert result.alert.decision == "surfaced"
    assert result.draft is not None
    assert "55" in result.draft.body


def test_run_case_from_documents_blocks_the_rule_when_extraction_needs_review(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    client = RecordedResponseClient(responses={"i94": {}, "i797": {}, "passport": {}})

    result = run_case_from_documents(
        store, clock_id="c1", client=client, mode="recorded", model_id="fake-model-id",
        documents={"i94": b"x", "i797": b"y", "passport": b"z"},
    )

    assert result.error is not None
    assert result.alert is None
    assert result.draft is None


def test_run_case_from_documents_is_deterministic_for_the_same_result(tmp_path):
    # F1 / identity: replaying the exact same documents through the same
    # (deterministic recorded) client must derive the same event_id, so the
    # existing draft is retrieved rather than treated as a new submission.
    store = Store(str(tmp_path / "ledger.db"))

    first = run_case_from_documents(
        store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id", documents=_specimen_bytes()
    )
    second = run_case_from_documents(
        store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id", documents=_specimen_bytes()
    )

    assert first.ref == second.ref
    assert second.alert.decision == "silent"
    assert second.draft.body == first.draft.body


def test_run_case_from_documents_gives_different_documents_a_distinct_identity_even_with_same_dates(tmp_path):
    # Amendment: two different document sets that happen to extract the same
    # dates must not collide — identity must be bound to document identity
    # (provenance) too, not just the extracted date values. Uses mode="live"
    # with a client exposing `.mode` so F2's specimen-byte verification
    # (which only applies in recorded mode, and would reject any bytes that
    # aren't the one bundled specimen) doesn't gate this — this is the
    # injected-environment path the real recorded-mode demo cannot exercise,
    # since it only ever accepts the bundled sample.
    import io

    from PIL import Image

    class LiveLikeClient:
        mode = "live"
        fallback_reason = None

        def __init__(self, recorded: RecordedResponseClient):
            self._recorded = recorded

        def converse(self, **kwargs):
            return self._recorded.converse(**kwargs)

    def _different_i94_bytes() -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (20, 20), color="blue").save(buf, format="PNG")
        return buf.getvalue()

    same_dates_response = RecordedResponseClient()  # identical fields/evidence both times
    store = Store(str(tmp_path / "ledger.db"))

    first_documents = _specimen_bytes()
    second_documents = {**_specimen_bytes(), "i94": _different_i94_bytes()}

    first = run_case_from_documents(
        store, clock_id="c1", client=LiveLikeClient(same_dates_response), mode="live", model_id="fake-model-id", documents=first_documents
    )
    second = run_case_from_documents(
        store, clock_id="c1", client=LiveLikeClient(same_dates_response), mode="live", model_id="fake-model-id", documents=second_documents
    )

    assert second.extraction.fields == first.extraction.fields  # identical extracted dates
    assert second.extraction.provenance["i94"] != first.extraction.provenance["i94"]  # different document
    assert second.ref["event_id"] != first.ref["event_id"]
    assert second.alert.decision == "surfaced"  # a genuinely new case, not deduplicated against the first
    assert second.draft is not None


def test_get_persisted_result_reconstructs_the_exact_stored_extraction(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_case_from_documents(
        store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id", documents=_specimen_bytes()
    )

    persisted = get_persisted_result(store, result.ref)
    assert persisted is not None
    assert persisted.fields == result.extraction.fields
    assert persisted.evidence == result.extraction.evidence
    assert persisted.provenance == result.extraction.provenance


def test_get_persisted_result_returns_none_for_an_unknown_ref(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    assert get_persisted_result(store, {"clock_id": "c1", "event_id": "doc-nonexistent", "rule_version": "v1"}) is None
