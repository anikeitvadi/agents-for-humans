"""The guardian agent: a Strands Agent whose only capabilities are the
engine's deterministic checks, exposed as tools.

This is the conversational front door ("do my documents disagree?", "did the
October bulletin change anything?", "is my speaker recalled?"). The agent
decides which check to run and reports the result; it never computes dates,
never determines status, and never gives legal advice. Every tool wraps the
same pack functions the web UI and the scheduled polls use, so the agent
cannot reach a conclusion the engine did not produce.

A fresh Agent is built per question so HTTP requests stay stateless and the
tool calls attributed to an answer are exactly the ones made for it.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from strands import Agent, tool
from strands.models import Model

from agent.engine.store import Store
from agent.packs.immigration.bulletin import BulletinLoadError, load_seeded_case, run_bulletin_poll
from agent.packs.immigration.pipeline import run_sample_case
from agent.packs.immigration.rules import check_i94_i797_discrepancy
from agent.packs.recalls.feed import RecallItem
from agent.packs.recalls.pipeline import run_recall_check

SYSTEM_PROMPT = (
    "You are the Immigration Status Guardian, a decision-support agent for people whose "
    "immigration paperwork is issued by different agencies on different clocks.\n\n"
    "Hard rules:\n"
    "1. You may only answer by calling your tools and reporting their results faithfully. "
    "Never compare or compute dates yourself; call check_document_dates.\n"
    "2. Never state whether someone is in status, out of status, safe to travel, or eligible "
    "for anything. Never give legal advice. Everything is a flag for the person's attorney.\n"
    "3. When a tool result's decision is 'surfaced', say that one thing needs the person's review "
    "and that an attorney-review draft is ready. When it is 'silent', say nothing new needs "
    "attention and give the reason from the tool.\n"
    "4. Mention the extraction or feed mode (recorded, live, fallback) when a tool reports one.\n"
    "5. Answer in a few plain sentences. If the tools cannot answer the question, say so and "
    "list what they can check."
)


def _jsonable(obj: Any) -> Any:
    """Plain JSON for a tool result: dataclasses (nested too) become dicts,
    anything else unknown becomes its string form."""

    def default(value):
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return dataclasses.asdict(value)
        return str(value)

    return json.loads(json.dumps(obj, default=default))


def _ok(payload: Any) -> dict:
    return {"status": "success", "content": [{"json": _jsonable(payload)}]}


def _err(message: str) -> dict:
    return {"status": "error", "content": [{"text": message}]}


def build_guardian_tools(
    store: Store,
    *,
    extraction_client,
    extraction_mode: str,
    model_id: str,
    recall_item: RecallItem,
    recall_mode: str,
    receipts_loader: Callable[[], dict],
    prior_bulletin_months: dict[str, str],
    draft_agent: Agent | None = None,
) -> list:
    """Wrap the engine's checks as Strands tools bound to this app's store,
    clients, and fixtures. Returned tools also work as plain functions."""

    @tool
    def check_document_dates(i94_admit_until: str, i797_valid_until: str) -> dict:
        """Compare an I-94 "admit until" date with an I-797 approval validity end date and report whether they disagree and by how many days. Pure date arithmetic on the two documents; it is never a status or lawful-presence determination.

        Args:
            i94_admit_until: The I-94 "Admit Until" date as YYYY-MM-DD.
            i797_valid_until: The I-797 approval notice validity end date as YYYY-MM-DD.
        """
        try:
            return _ok(check_i94_i797_discrepancy(i94_admit_until, i797_valid_until))
        except ValueError as exc:
            return _err(f"Dates must be YYYY-MM-DD: {exc}")

    @tool
    def run_sample_case_check() -> dict:
        """Run the full check on the built-in sample case: extract fields from the three specimen documents (I-94, I-797, passport), compare the dates, pass the result through the decision gate, and prepare an attorney-review draft if something surfaced. Repeating it for the same case stays silent but still returns the existing draft."""
        result = run_sample_case(
            store,
            clock_id="demo-clock",
            event_id="demo-event",
            client=extraction_client,
            mode=extraction_mode,
            model_id=model_id,
            agent=draft_agent,
        )
        if result.error and result.alert is None:
            return _err(f"{result.error} (extraction mode: {result.extraction.mode})")
        return _ok(
            {
                "extraction_mode": result.extraction.mode,
                "fields": result.extraction.fields,
                "needs_review": result.extraction.needs_review,
                "error": result.error,
                "decision": result.alert.decision if result.alert else None,
                "reason": result.alert.reason if result.alert else None,
                "draft": result.draft,
            }
        )

    @tool
    def check_visa_bulletin(month: str) -> dict:
        """Check one monthly Visa Bulletin for the seeded case (EB2-India): whether the priority date is current under the chart USCIS designated for that month, and whether that surfaces a filing-window ping. Only captured months are available, currently 2025-09 and 2025-10.

        Args:
            month: Bulletin month as YYYY-MM, for example 2025-10.
        """
        try:
            case = load_seeded_case()
            result = run_bulletin_poll(
                store,
                clock_id="bulletin-clock",
                month=month,
                case=case,
                agent=draft_agent,
                previous_month=prior_bulletin_months.get(month),
            )
        except BulletinLoadError as exc:
            return _err(str(exc))
        if result.error and result.alert is None:
            return _err(result.error)
        return _ok(
            {
                "case_name": case.case_name,
                "month": month,
                "error": result.error,
                "cutoff_status": result.cutoff.status if result.cutoff else None,
                "decision": result.alert.decision if result.alert else None,
                "reason": result.alert.reason if result.alert else None,
                "draft": result.draft,
            }
        )

    @tool
    def check_recall(receipt: str = "seeded") -> dict:
        """Match a saved receipt against the consumer product recall feed (CPSC) and report the remedy if it matches. Demo scope: exact manufacturer and product match against the seeded receipts.

        Args:
            receipt: Which saved receipt to check: "seeded" (the speaker) or "unmatched" (the earbuds).
        """
        receipts = receipts_loader()
        key = "seeded_receipt" if receipt != "unmatched" else "unmatched_receipt"
        result = run_recall_check(store, clock_id="recall-clock", recall_item=recall_item, receipt=receipts[key])
        return _ok(
            {
                "feed_mode": recall_mode,
                "matched": result.match.matched,
                "message": result.match.message,
                "demo_scope": result.match.demo_scope,
                "decision": result.alert.decision,
                "reason": result.alert.reason,
                "draft": result.draft,
            }
        )

    return [check_document_dates, run_sample_case_check, check_visa_bulletin, check_recall]


def tool_names(tools: list) -> list[str]:
    return [t.tool_spec["name"] for t in tools]


def build_guardian_model(model_id: str) -> Model | None:
    """A Bedrock-backed model when AWS credentials exist, else None (the
    agent is then reported as unavailable rather than failing at call time)."""
    from agent.llm.draft import _has_aws_credentials

    if not _has_aws_credentials():
        return None
    from strands.models import BedrockModel

    return BedrockModel(model_id=model_id)


def build_guardian_agent(model: Model, tools: list) -> Agent:
    return Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, callback_handler=None)


@dataclass
class AskResult:
    answer: str
    tools_called: list[str] = field(default_factory=list)
    error: str | None = None


def ask_guardian(model: Model, tools: list, question: str) -> AskResult:
    """Answer one question with a fresh agent. Any model/agent failure is
    returned as `error`, never raised, so callers degrade visibly."""
    agent = build_guardian_agent(model, tools)
    try:
        result = agent(question)
    except Exception as exc:  # noqa: BLE001 - surface, don't crash the request
        return AskResult(answer="", error=f"{type(exc).__name__}: {exc}")
    called = [
        block["toolUse"]["name"]
        for message in agent.messages
        for block in message.get("content", [])
        if "toolUse" in block
    ]
    return AskResult(answer=str(result).strip(), tools_called=called)
