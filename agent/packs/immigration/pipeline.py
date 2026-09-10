"""Ties the immigration pack together: deterministic rule -> engine
(gate + persistence) -> attorney draft, only when the gate surfaces.
No LLM call is required for the discrepancy check itself; drafting will
use a Strands Agent when one is supplied (see agent/llm/draft.py), and
falls back to the deterministic core otherwise.
"""

from dataclasses import dataclass

from strands import Agent

from agent.engine.engine import RuleOutcome, process_event
from agent.engine.schema import Alert, Clock, Event
from agent.engine.store import Store
from agent.llm.draft import DraftResult, build_attorney_draft
from agent.packs.immigration.rules import check_i94_i797_discrepancy


@dataclass
class PipelineResult:
    alert: Alert
    draft: DraftResult | None


def run_discrepancy_check(
    store: Store,
    clock_id: str,
    event_id: str,
    fields: dict,
    agent: Agent | None = None,
) -> PipelineResult:
    discrepancy = check_i94_i797_discrepancy(
        i94_admit_until=fields["admit_until"], i797_valid_until=fields["i797_valid_until"]
    )

    clock = Clock(clock_id=clock_id, user_id="demo-user", module="immigration", rule_id="i94_i797_discrepancy", state="quiet")
    event = Event(event_id=event_id, source="document_upload", effective_date=fields["admit_until"], rule_version="v1", payload=fields)
    outcome = RuleOutcome(material=discrepancy.discrepant, actionable=discrepancy.discrepant, window_open=discrepancy.discrepant)

    alert = process_event(store, clock, event, outcome)

    draft = None
    if alert.decision == "surfaced":
        draft = build_attorney_draft(
            rule_message=discrepancy.message,
            subject_facts={"case_name": fields.get("case_name", "immigration documents")},
            agent=agent,
        )

    return PipelineResult(alert=alert, draft=draft)
