from agent.engine.store import Store
from agent.packs.immigration.pipeline import run_discrepancy_check


def _sample_fields(i94="2026-11-03", i797="2026-12-28"):
    return {"admit_until": i94, "i797_valid_until": i797, "case_name": "Sample Case"}


def test_discrepant_case_surfaces_with_attorney_draft(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_discrepancy_check(store, clock_id="c1", event_id="evt-1", fields=_sample_fields())

    assert result.alert.decision == "surfaced"
    assert result.draft is not None
    assert "55" in result.draft.body


def test_matching_dates_stay_silent_and_produce_no_draft(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_discrepancy_check(
        store, clock_id="c1", event_id="evt-1", fields=_sample_fields(i94="2026-12-28", i797="2026-12-28")
    )

    assert result.alert.decision == "silent"
    assert result.draft is None


def test_reprocessing_same_event_does_not_produce_a_second_ping_but_keeps_the_draft(tmp_path):
    # C2: a repeat poll (e.g. after a page reload or process restart) must
    # not surface a second alert, but the unresolved draft from the first
    # surfaced alert must still be retrievable — not silently dropped.
    store = Store(str(tmp_path / "ledger.db"))

    first = run_discrepancy_check(store, clock_id="c1", event_id="evt-1", fields=_sample_fields())
    second = run_discrepancy_check(store, clock_id="c1", event_id="evt-1", fields=_sample_fields())

    assert first.alert.decision == "surfaced"
    assert second.alert.decision == "silent"
    assert second.draft is not None
    assert second.draft.subject == first.draft.subject
    assert second.draft.body == first.draft.body


def test_draft_is_retrievable_after_restart(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))
    first = run_discrepancy_check(store, clock_id="c1", event_id="evt-1", fields=_sample_fields())

    restarted_store = Store(str(db_path))
    replayed = run_discrepancy_check(restarted_store, clock_id="c1", event_id="evt-1", fields=_sample_fields())

    assert replayed.alert.decision == "silent"
    assert replayed.draft is not None
    assert replayed.draft.body == first.draft.body
