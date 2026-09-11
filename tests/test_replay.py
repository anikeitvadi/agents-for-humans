from agent.engine.schema import Alert, Event
from agent.engine.store import Store


def _bulletin_event():
    return Event(
        event_id="evt-2026-09-bulletin",
        source="visa_bulletin",
        effective_date="2026-09-15",
        rule_version="v1",
        payload={"chart": "final_action"},
    )


def _surfaced_alert():
    return Alert(
        clock_id="c1",
        event_id="evt-2026-09-bulletin",
        rule_version="v1",
        decision="surfaced",
        reason="passed all gates",
    )


def test_saving_the_same_event_twice_is_a_noop(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))

    first = store.save_event(_bulletin_event())
    second = store.save_event(_bulletin_event())

    assert first is True
    assert second is False


def test_polling_same_bulletin_twice_produces_no_duplicate_alert(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))

    store.save_event(_bulletin_event())
    first_alert_new = store.save_alert(_surfaced_alert())
    store.save_event(_bulletin_event())  # polled again
    second_alert_new = store.save_alert(_surfaced_alert())  # same rule evaluates same event again

    assert first_alert_new is True
    assert second_alert_new is False
    assert len(store.list_alerts("c1")) == 1


def test_dedup_survives_process_restart(tmp_path):
    db_path = tmp_path / "ledger.db"

    store_before_restart = Store(str(db_path))
    store_before_restart.save_alert(_surfaced_alert())

    # Simulate a restart: a fresh Store instance pointed at the same file.
    store_after_restart = Store(str(db_path))
    still_duplicate = store_after_restart.save_alert(_surfaced_alert())

    assert still_duplicate is False
    assert len(store_after_restart.list_alerts("c1")) == 1
