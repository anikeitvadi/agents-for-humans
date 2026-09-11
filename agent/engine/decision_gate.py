"""The decision gate: the four predicates that decide surface-vs-stay-silent
(architecture-spec.md §6). Pure, deterministic — no LLM involved.
"""

from dataclasses import dataclass, field

from agent.engine.schema import Alert


@dataclass
class GateInputs:
    clock_id: str
    event_id: str
    rule_version: str
    material: bool
    actionable: bool
    window_open: bool
    prior_alerts: list[Alert] = field(default_factory=list)


def evaluate_gate(inputs: GateInputs) -> Alert:
    failed: list[str] = []
    if not inputs.material:
        failed.append("materiality")
    if not inputs.actionable:
        failed.append("actionability")
    if not inputs.window_open:
        failed.append("window")
    if _already_surfaced(inputs):
        failed.append("novelty")

    if failed:
        return Alert(
            clock_id=inputs.clock_id,
            event_id=inputs.event_id,
            rule_version=inputs.rule_version,
            decision="silent",
            reason=f"failed: {', '.join(failed)}",
        )

    return Alert(
        clock_id=inputs.clock_id,
        event_id=inputs.event_id,
        rule_version=inputs.rule_version,
        decision="surfaced",
        reason="passed materiality, actionability, window, novelty",
    )


def _already_surfaced(inputs: GateInputs) -> bool:
    # rule_version is part of the alert key: a rule-version change is a
    # distinct evaluation and must not inherit novelty suppression from an
    # older version's surfaced alert.
    return any(
        alert.clock_id == inputs.clock_id
        and alert.event_id == inputs.event_id
        and alert.rule_version == inputs.rule_version
        and alert.decision == "surfaced"
        for alert in inputs.prior_alerts
    )
