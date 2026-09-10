from pathlib import Path

from agent.engine.store import Store
from agent.packs.immigration.bulletin import (
    BulletinLoadError,
    SeededCase,
    load_bulletin_month,
    load_seeded_case,
    run_bulletin_poll,
)


def _case():
    return SeededCase(case_name="Sample Bulletin Case", priority_date="2013-06-15", category="EB2-India", chargeability="India")


def test_load_seeded_case_matches_fixture():
    case = load_seeded_case()

    assert case.category == "EB2-India"
    assert case.priority_date


def test_load_september_2025_bulletin_uses_final_action_chart():
    month = load_bulletin_month("2025-09")

    assert month.chart.chart_type == "final_action"
    assert month.chart.cutoffs["EB2-India"] == "2013-01-01"
    assert month.designated_chart_type == "final_action"


def test_load_october_2025_bulletin_uses_dates_for_filing_chart():
    month = load_bulletin_month("2025-10")

    assert month.chart.chart_type == "dates_for_filing"
    assert month.chart.cutoffs["EB2-India"] == "2013-12-01"
    assert month.designated_chart_type == "dates_for_filing"


def test_load_missing_month_raises_load_error():
    import pytest

    with pytest.raises(BulletinLoadError):
        load_bulletin_month("1999-01")


def test_load_malformed_fixture_raises_load_error_not_a_crash(tmp_path):
    import pytest

    (tmp_path / "2030-01.json").write_text('{"dos_bulletin": {}}')

    with pytest.raises(BulletinLoadError):
        load_bulletin_month("2030-01", bulletins_dir=tmp_path)


def test_september_poll_is_not_current_and_stays_silent(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-09", case=_case())

    assert result.error is None
    assert result.cutoff.status == "not_current"
    assert result.alert.decision == "silent"
    assert result.draft is None


def test_october_poll_turns_current_and_surfaces_one_attorney_alert(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-09", case=_case())

    result = run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-10", case=_case(), previous_month="2025-09")

    assert result.error is None
    assert result.cutoff.status == "current"
    assert result.alert.decision == "surfaced"
    assert result.draft is not None


def test_repeat_october_poll_produces_no_second_ping_but_keeps_the_draft(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    first = run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-10", case=_case())

    second = run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-10", case=_case())

    assert second.alert.decision == "silent"
    assert second.draft is not None
    assert second.draft.body == first.draft.body


def test_october_poll_survives_restart_without_duplicate(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))
    first = run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-10", case=_case())

    restarted_store = Store(str(db_path))
    replayed = run_bulletin_poll(restarted_store, clock_id="bulletin-clock", month="2025-10", case=_case())

    assert replayed.alert.decision == "silent"
    assert replayed.draft is not None
    assert replayed.draft.body == first.draft.body


def test_missing_month_feed_produces_visible_error_not_a_crash(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    result = run_bulletin_poll(store, clock_id="bulletin-clock", month="2099-01", case=_case())

    assert result.error is not None
    assert result.alert is None
    assert result.draft is None


def test_mismatched_chart_type_across_months_skips_retrogression_not_crash(tmp_path):
    # September (final_action) and October (dates_for_filing) are different
    # published series — comparing them directly would be a chart-type
    # mismatch, not a real backward move. The poll must not claim
    # retrogression here; the underlying cutoff comparison for October
    # still succeeds on its own designated chart.
    store = Store(str(tmp_path / "ledger.db"))

    result = run_bulletin_poll(store, clock_id="bulletin-clock", month="2025-10", case=_case(), previous_month="2025-09")

    assert result.error is None
    assert result.cutoff.status == "current"
