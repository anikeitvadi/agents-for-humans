"""Deterministic control flow: validate -> evaluate rules -> run the
decision gate -> persist. Plain application code — the LLM is never in
this loop. Callers pass a RuleOutcome already computed by a pack's
deterministic rules module (or by extraction); this module only owns
ordering and persistence, never rule logic itself.
"""

from dataclasses import dataclass
from typing import Callable

from agent.engine.decision_gate import GateInputs, evaluate_gate
from agent.engine.schema import Alert, Clock, Event
from agent.engine.store import Store
from agent.llm.draft import DraftResult


@dataclass
class RuleOutcome:
    material: bool
    actionable: bool
    window_open: bool


def process_event(
    store: Store, clock: Clock, event: Event, outcome: RuleOutcome, *, expected_epoch: int | None = None
) -> Alert:
    store.save_event(event, expected_epoch=expected_epoch)
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
    claimed = store.save_alert(alert, expected_epoch=expected_epoch)

    if alert.decision == "surfaced" and not claimed:
        # This caller's local gate evaluation said "surfaced", but the
        # store's atomic UPSERT (agent/engine/store.py::save_alert) reports
        # no new claim was made — another caller already claimed this exact
        # row between our read of prior_alerts and our write (R5). Only the
        # successful claimant may report a new surfaced decision; a losing
        # concurrent caller must report no new notification, never a second
        # "surfaced" for one stored row.
        return Alert(
            clock_id=alert.clock_id,
            event_id=alert.event_id,
            rule_version=alert.rule_version,
            decision="silent",
            reason="failed: novelty (lost concurrent claim)",
        )
    return alert


def ensure_draft(
    store: Store,
    clock: Clock,
    event: Event,
    should_have_draft: bool,
    build_draft: Callable[[], DraftResult],
    *,
    expected_epoch: int | None = None,
) -> DraftResult | None:
    """Persists and recovers draft work independently of alert novelty (R4).

    A pack's rule outcome — not `alert.decision` — decides whether a draft
    should exist for this event: a case that is genuinely discrepant/
    actionable must always end up with a ready draft, whether this is the
    first surfacing, a routine silent replay, or a replay recovering from a
    crash that persisted the surfaced alert but never reached the
    draft-save step. `store.save_draft`'s sticky-on-ready upsert makes
    calling `build_draft` again on every non-ready replay safe: a prior
    ready draft is never overwritten, and a race with another claimant is
    resolved by re-reading the stored row after the write.
    """
    if not should_have_draft:
        return None

    existing = store.get_draft(clock_id=clock.clock_id, event_id=event.event_id, rule_version=event.rule_version)
    if existing is not None and existing.status == "ready":
        return DraftResult(
            subject=existing.subject, body=existing.body, used_llm_personalization=bool(existing.used_llm_personalization)
        )

    built = build_draft()
    store.save_draft(
        clock_id=clock.clock_id,
        event_id=event.event_id,
        rule_version=event.rule_version,
        status="ready",
        subject=built.subject,
        body=built.body,
        used_llm_personalization=built.used_llm_personalization,
        expected_epoch=expected_epoch,
    )
    final = store.get_draft(clock_id=clock.clock_id, event_id=event.event_id, rule_version=event.rule_version)
    if final is None or final.status != "ready":
        return built
    return DraftResult(subject=final.subject, body=final.body, used_llm_personalization=bool(final.used_llm_personalization))
