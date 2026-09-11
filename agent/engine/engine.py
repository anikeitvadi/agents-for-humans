"""Deterministic control flow: validate -> evaluate rules -> run the
decision gate -> persist. Plain application code — the LLM is never in
this loop. Callers pass a RuleOutcome already computed by a pack's
deterministic rules module (or by extraction); this module only owns
ordering and persistence, never rule logic itself.
"""

from dataclasses import dataclass

from agent.engine.decision_gate import GateInputs, evaluate_gate
from agent.engine.schema import Alert, Clock, Event
from agent.engine.store import Store


@dataclass
class RuleOutcome:
    material: bool
    actionable: bool
    window_open: bool


def process_event(store: Store, clock: Clock, event: Event, outcome: RuleOutcome) -> Alert:
    store.save_event(event)
    prior_alerts = store.list_alerts(clock.clock_id)

    gate_inputs = GateInputs(
        clock_id=clock.clock_id,
        event_id=event.event_id,
        rule_version=event.rule_version,
        material=outcome.material,
        actionable=outcome.actionable,
        window_open=outcome.window_open,
        prior_alerts=prior_alerts,
    )
    alert = evaluate_gate(gate_inputs)
    store.save_alert(alert)
    return alert
