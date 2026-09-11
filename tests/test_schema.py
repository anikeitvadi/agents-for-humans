import pytest
from pydantic import ValidationError

from agent.engine.schema import Alert, Clock, Event


def test_clock_rejects_invalid_state():
    with pytest.raises(ValidationError):
        Clock(
            clock_id="c1",
            user_id="u1",
            module="immigration",
            rule_id="i94_i797_discrepancy",
            state="not_a_real_state",
        )


def test_clock_accepts_valid_state():
    clock = Clock(
        clock_id="c1",
        user_id="u1",
        module="immigration",
        rule_id="i94_i797_discrepancy",
        state="quiet",
    )
    assert clock.state == "quiet"


def test_event_has_stable_identity_fields():
    event = Event(
        event_id="evt-2026-09-bulletin",
        source="visa_bulletin",
        effective_date="2026-09-15",
        rule_version="v1",
        payload={"chart": "final_action"},
    )
    assert event.event_id == "evt-2026-09-bulletin"
    assert event.payload["chart"] == "final_action"


def test_alert_dedup_key_is_stable_for_same_inputs():
    alert_a = Alert(
        clock_id="c1",
        event_id="evt-1",
        rule_version="v1",
        decision="surfaced",
    )
    alert_b = Alert(
        clock_id="c1",
        event_id="evt-1",
        rule_version="v1",
        decision="surfaced",
    )
    assert alert_a.dedup_key() == alert_b.dedup_key()


def test_alert_dedup_key_differs_on_rule_version():
    alert_a = Alert(clock_id="c1", event_id="evt-1", rule_version="v1", decision="surfaced")
    alert_b = Alert(clock_id="c1", event_id="evt-1", rule_version="v2", decision="surfaced")
    assert alert_a.dedup_key() != alert_b.dedup_key()
