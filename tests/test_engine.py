from agent.engine.engine import RuleOutcome, process_event
from agent.engine.schema import Clock, Event
from agent.engine.store import Store


def _clock():
    return Clock(clock_id="c1", user_id="u1", module="immigration", rule_id="i94_i797_discrepancy", state="quiet")


def _event():
    return Event(
        event_id="evt-1",
        source="document_upload",
        effective_date="2026-09-10",
        rule_version="v1",
        payload={},
    )


def test_first_pass_surfaces_when_all_predicates_pass(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    outcome = RuleOutcome(material=True, actionable=True, window_open=True)

    alert = process_event(store, _clock(), _event(), outcome)

    assert alert.decision == "surfaced"
    assert len(store.list_alerts("c1")) == 1


def test_reprocessing_the_same_event_does_not_surface_twice(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    outcome = RuleOutcome(material=True, actionable=True, window_open=True)

    process_event(store, _clock(), _event(), outcome)
    second_alert = process_event(store, _clock(), _event(), outcome)

    assert second_alert.decision == "silent"
    assert len(store.list_alerts("c1")) == 1


def test_window_opening_after_silent_surfaces_once_then_stays_silent(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    clock = _clock()
    event = _event()

    closed = process_event(store, clock, event, RuleOutcome(material=True, actionable=True, window_open=False))
    assert closed.decision == "silent"

    opened_first = process_event(store, clock, event, RuleOutcome(material=True, actionable=True, window_open=True))
    assert opened_first.decision == "surfaced"

    opened_again = process_event(store, clock, event, RuleOutcome(material=True, actionable=True, window_open=True))
    assert opened_again.decision == "silent"

    stored = store.list_alerts("c1")
    assert len(stored) == 1
    assert stored[0].decision == "surfaced"


def test_dedup_survives_restart_after_silent_to_surfaced_transition(tmp_path):
    db_path = tmp_path / "ledger.db"
    clock = _clock()
    event = _event()

    store = Store(str(db_path))
    process_event(store, clock, event, RuleOutcome(material=True, actionable=True, window_open=False))
    process_event(store, clock, event, RuleOutcome(material=True, actionable=True, window_open=True))

    # Simulate a restart: a fresh Store instance pointed at the same file.
    restarted_store = Store(str(db_path))
    replayed = process_event(restarted_store, clock, event, RuleOutcome(material=True, actionable=True, window_open=True))

    assert replayed.decision == "silent"
    assert len(restarted_store.list_alerts("c1")) == 1


def test_rule_version_change_is_not_suppressed_by_prior_surfaced_alert(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    clock = _clock()
    outcome = RuleOutcome(material=True, actionable=True, window_open=True)

    event_v1 = Event(event_id="evt-1", source="document_upload", effective_date="2026-09-10", rule_version="v1", payload={})
    event_v2 = Event(event_id="evt-1", source="document_upload", effective_date="2026-09-10", rule_version="v2", payload={})

    process_event(store, clock, event_v1, outcome)
    alert_v2 = process_event(store, clock, event_v2, outcome)

    assert alert_v2.decision == "surfaced"


def test_rule_evaluation_happens_before_persistence_not_inside_a_prompt(tmp_path):
    """The engine module must not import or depend on any LLM/agent
    machinery — evaluation and gating are plain application code."""
    import agent.engine.engine as engine_module

    source = open(engine_module.__file__).read()
    assert "strands" not in source.lower()
    assert "agent(" not in source.lower()
