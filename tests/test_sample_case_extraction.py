from agent.engine.store import Store
from agent.llm.document_client import RecordedResponseClient
from agent.packs.immigration.pipeline import extract_sample_case_fields, run_sample_case


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

    result = run_sample_case(
        store, clock_id="c1", event_id="evt-1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id"
    )

    assert result.error is None
    assert result.alert.decision == "surfaced"
    assert result.draft is not None
    assert "55" in result.draft.body
    assert result.extraction.mode == "recorded"


def test_run_sample_case_draft_survives_repeat_call_and_restart(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))

    first = run_sample_case(
        store, clock_id="c1", event_id="evt-1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id"
    )

    restarted_store = Store(str(db_path))
    replayed = run_sample_case(
        restarted_store, clock_id="c1", event_id="evt-1", client=RecordedResponseClient(), mode="recorded", model_id="fake-model-id"
    )

    assert replayed.alert.decision == "silent"
    assert replayed.draft is not None
    assert replayed.draft.body == first.draft.body


def test_run_sample_case_does_not_run_the_rule_when_extraction_needs_review(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    client = RecordedResponseClient(responses={"i94": {}, "i797": {}, "passport": {}})

    result = run_sample_case(store, clock_id="c1", event_id="evt-1", client=client, mode="recorded", model_id="fake-model-id")

    assert result.error is not None
    assert result.alert is None
    assert result.draft is None


class _RaisingClient:
    """Stands in for a Bedrock client whose Converse call fails outright
    (account block, network, throttling) rather than returning bad JSON."""

    def converse(self, **kwargs):
        raise RuntimeError("Error 002: Access to Bedrock models is not allowed for this account")


def test_extraction_api_failure_is_a_visible_error_not_a_crash(tmp_path):
    from agent.engine.store import Store
    from agent.packs.immigration.pipeline import run_sample_case

    store = Store(str(tmp_path / "ledger.db"))

    result = run_sample_case(
        store, clock_id="c1", event_id="evt-1", client=_RaisingClient(), mode="live", model_id="m"
    )

    assert result.alert is None
    assert result.draft is None
    assert result.extraction.mode == "live"
    assert result.extraction.needs_review is True
    assert "Error 002" in result.error
