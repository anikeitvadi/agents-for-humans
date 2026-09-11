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
from agent.packs.immigration.pipeline import get_persisted_result, run_sample_case
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
    "list what they can check.\n"
    "6. If asked about the documents the person just uploaded, use check_uploaded_case, never "
    "run_sample_case_check — that tool is the separate bundled demo sample, not their case."
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
    current_submission_ref: dict[str, str] | None = None,
) -> list:
    """Wrap the engine's checks as Strands tools bound to this app's store,
    clients, and fixtures. Returned tools also work as plain functions.

    `current_submission_ref` is the {clock_id, event_id, rule_version} of a
    specific document upload the caller wants the agent able to discuss —
    typically supplied per-request from the UI's last /api/process-documents
    response, not held as server-side "last upload" state. Without it,
    check_uploaded_case reports unavailable rather than silently falling
    back to the bundled sample."""

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
    def check_uploaded_case() -> dict:
        """Report the discrepancy check result for the specific documents the person just uploaded and processed through the upload flow — never the bundled demo sample. Requires that this question was asked with a submission reference from a completed upload; otherwise reports that no uploaded case is available."""
        if current_submission_ref is None:
            return _err("No uploaded case is available for this question. Process documents through the upload flow first, then ask again.")
        persisted = get_persisted_result(store, current_submission_ref)
        if persisted is None:
            return _err("The referenced submission was not found — it may have been cleared by a reset. Process documents again.")
        alert = store.get_alert(**current_submission_ref)
        draft = store.get_draft(**current_submission_ref)
        return _ok(
            {
                "extraction_mode": persisted.mode,
                "mode_reason": persisted.mode_reason,
                "fields": persisted.fields,
                "needs_review": persisted.needs_review,
                "decision": alert.decision if alert else None,
                "reason": alert.reason if alert else None,
                "draft": (
                    {"subject": draft.subject, "body": draft.body, "used_llm_personalization": bool(draft.used_llm_personalization)}
                    if draft is not None and draft.status == "ready"
                    else None
                ),
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

    return [check_document_dates, run_sample_case_check, check_uploaded_case, check_visa_bulletin, check_recall]


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
class TraceStep:
    """One inspectable execution fact: which tool ran, on what input, and
    what the deterministic engine returned. Never model reasoning."""

    step: int
    tool: str
    tool_use_id: str
    input: dict
    status: str  # "success" | "error" | "missing" (tool was called but no result was recorded)
    mode: str | None  # extraction_mode / feed_mode reported by the tool, if any
    decision: str | None  # deterministic gate decision, if the tool ran the gate
    reason: str | None
    persisted_draft: bool
    summary: str


@dataclass
class AskResult:
    answer: str
    tools_called: list[str] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)
    error: str | None = None

    def trace_dicts(self) -> list[dict]:
        return [dataclasses.asdict(step) for step in self.trace]


def _safe_input(value: Any, limit: int = 120) -> Any:
    if isinstance(value, dict):
        return {k: _safe_input(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe_input(v, limit) for v in value]
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "…"
    return value


def build_trace(messages: list[dict]) -> list[TraceStep]:
    """Pair every toolUse block the model emitted with the toolResult block
    the agent fed back, in call order, straight from the Strands message
    history. Only execution facts are extracted."""
    results: dict[str, dict] = {}
    for message in messages:
        for block in message.get("content", []):
            if "toolResult" in block:
                results[block["toolResult"].get("toolUseId", "")] = block["toolResult"]

    steps: list[TraceStep] = []
    for message in messages:
        for block in message.get("content", []):
            if "toolUse" not in block:
                continue
            use = block["toolUse"]
            result = results.get(use.get("toolUseId", ""))
            payload: dict = {}
            text = ""
            status = "missing"
            if result is not None:
                status = result.get("status", "success")
                for content in result.get("content", []):
                    if "json" in content and isinstance(content["json"], dict):
                        payload = content["json"]
                        break
                    if "text" in content and not text:
                        text = content["text"]
            summary = (
                payload.get("error")
                or payload.get("message")
                or payload.get("reason")
                or text
                or ("no result recorded" if result is None else "")
            )
            steps.append(
                TraceStep(
                    step=len(steps) + 1,
                    tool=use.get("name", "?"),
                    tool_use_id=use.get("toolUseId", ""),
                    input=_safe_input(use.get("input") or {}),
                    status=status,
                    mode=payload.get("extraction_mode") or payload.get("feed_mode"),
                    decision=payload.get("decision"),
                    reason=payload.get("reason"),
                    persisted_draft=bool(payload.get("draft")),
                    summary=str(summary)[:300],
                )
            )
    return steps


def ask_guardian(model: Model, tools: list, question: str) -> AskResult:
    """Answer one question with a fresh agent. Any model/agent failure is
    returned as `error`, never raised, so callers degrade visibly."""
    agent = build_guardian_agent(model, tools)
    try:
        result = agent(question)
    except Exception as exc:  # noqa: BLE001 - surface, don't crash the request
        return AskResult(answer="", error=f"{type(exc).__name__}: {exc}")
    trace = build_trace(agent.messages)
    return AskResult(answer=str(result).strip(), tools_called=[step.tool for step in trace], trace=trace)
