from agent.engine.decision_gate import GateInputs, evaluate_gate
from agent.engine.schema import Alert


def _base_inputs(**overrides):
    defaults = dict(
        clock_id="c1",
        event_id="evt-1",
        rule_version="v1",
        material=True,
        actionable=True,
        window_open=True,
        prior_alerts=[],
    )
    defaults.update(overrides)
    return GateInputs(**defaults)


def test_all_predicates_pass_surfaces_alert():
    alert = evaluate_gate(_base_inputs())
    assert alert.decision == "surfaced"


def test_fails_materiality_stays_silent():
    alert = evaluate_gate(_base_inputs(material=False))
    assert alert.decision == "silent"
    assert "materiality" in alert.reason


def test_fails_actionability_stays_silent():
    alert = evaluate_gate(_base_inputs(actionable=False))
    assert alert.decision == "silent"
    assert "actionability" in alert.reason


def test_fails_window_stays_silent():
    alert = evaluate_gate(_base_inputs(window_open=False))
    assert alert.decision == "silent"
    assert "window" in alert.reason


def test_fails_novelty_when_already_surfaced_for_same_event():
    prior = [Alert(clock_id="c1", event_id="evt-1", rule_version="v1", decision="surfaced")]
    alert = evaluate_gate(_base_inputs(prior_alerts=prior))
    assert alert.decision == "silent"
    assert "novelty" in alert.reason


def test_novelty_ignores_alerts_for_a_different_event():
    prior = [Alert(clock_id="c1", event_id="evt-OTHER", rule_version="v1", decision="surfaced")]
    alert = evaluate_gate(_base_inputs(prior_alerts=prior))
    assert alert.decision == "surfaced"
