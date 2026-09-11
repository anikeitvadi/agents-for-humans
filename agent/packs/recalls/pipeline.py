"""Ties the recall pack together: match -> engine (gate + persistence) ->
remedy message, only when the gate surfaces. Same shared engine/gate/store
path as the immigration pack (C4) — proves the loop is generic, not a
second bespoke pipeline. No LLM call: the remedy message is the rule's own
deterministic output (docs/architecture-spec.md's recall-to-remedy scope
is a plain "refund or voucher?" ping, not a drafted email).
"""

from dataclasses import dataclass

from agent.engine.engine import RuleOutcome, ensure_draft, process_event
from agent.engine.schema import Alert, Clock, Event
from agent.engine.store import Store
from agent.llm.draft import DraftResult
from agent.packs.recalls.feed import RecallItem
from agent.packs.recalls.rules import RecallMatchResult, match_recall_to_receipt


@dataclass
class RecallCheckResult:
    alert: Alert
    draft: DraftResult | None
    match: RecallMatchResult


def run_recall_check(store: Store, clock_id: str, recall_item: RecallItem, receipt: dict) -> RecallCheckResult:
    match = match_recall_to_receipt(recall_item.as_dict(), receipt)

    clock = Clock(clock_id=clock_id, user_id="demo-user", module="recalls", rule_id="recall_receipt_match", state="quiet")
    event = Event(
        event_id=f"recall-{recall_item.recall_id}-{receipt.get('receipt_id', 'unknown')}",
        source="cpsc_recall_feed",
        effective_date=recall_item.recall_date,
        rule_version="v1",
        payload={"recall_id": recall_item.recall_id, "receipt_id": receipt.get("receipt_id")},
    )
    outcome = RuleOutcome(material=match.matched, actionable=match.matched, window_open=match.matched)

    alert = process_event(store, clock, event, outcome)

    draft = ensure_draft(
        store,
        clock,
        event,
        should_have_draft=match.matched,
        build_draft=lambda: DraftResult(
            subject=f"Recall remedy available: {recall_item.product_name}", body=match.message, used_llm_personalization=False
        ),
    )

    return RecallCheckResult(alert=alert, draft=draft, match=match)
