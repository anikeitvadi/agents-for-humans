"""AgentCore Runtime entrypoint (Day-3 item; docs/architecture-spec.md §4.1, §9).

Wraps the same deterministic pipeline the local FastAPI app uses. No engine or
pack logic lives here. Two payload shapes:

  {}                                  -> run the sample case (three specimen
                                         images -> extraction -> date-gap rule
                                         -> gate -> attorney draft). Extraction
                                         replays the recorded Bedrock response
                                         unless "extraction": "live" is passed.
  {"fields": {...}}                   -> skip extraction, run the rule on the
                                         given fields (admit_until,
                                         i797_valid_until, case_name).
  {"prompt": "..."}                   -> ask the guardian agent: a Strands
                                         Agent whose only tools are the
                                         engine's checks (agent/llm/guardian.py).

Optional keys on both: "clock_id", "event_id" (dedup identity in the ledger).
Every response labels the extraction mode; a recorded replay is never
presented as a live parse.

Local: `python deploy/agentcore_entrypoint.py` then
  curl -X POST localhost:8080/invocations -H 'content-type: application/json' -d '{}'
Cloud: see README "AgentCore Runtime".
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# The Runtime (and `python deploy/agentcore_entrypoint.py`) puts deploy/ on
# sys.path, not the repo root; make the `agent` package importable either way.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

from agent.config import BEDROCK_MODEL_ID  # noqa: E402
from agent.engine.store import Store  # noqa: E402
from agent.llm.document_client import RecordedResponseClient, build_extraction_client  # noqa: E402
from agent.llm.draft import DraftResult, build_bedrock_agent  # noqa: E402
from agent.llm.guardian import ask_guardian, build_guardian_model, build_guardian_tools, tool_names  # noqa: E402
from agent.packs.immigration.bulletin import PRIOR_CAPTURED_MONTH  # noqa: E402
from agent.packs.immigration.pipeline import run_discrepancy_check, run_sample_case  # noqa: E402
from agent.packs.recalls.feed import get_recall_item  # noqa: E402

RECEIPTS_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "recalls" / "receipts.json"

DB_PATH = Path(os.environ.get("GUARDIAN_DB_PATH", "/tmp/immigration-status-guardian/agentcore_ledger.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = BedrockAgentCoreApp()
_store = Store(str(DB_PATH))
# A real Strands Agent on Bedrock when credentials exist (always true inside
# the Runtime), else None; build_attorney_draft falls back to its fixed core
# either way, so a Bedrock failure degrades personalization, never correctness.
_agent = build_bedrock_agent(model_id=BEDROCK_MODEL_ID)

# Guardian agent (prompt path). Tools use recorded extraction so a judge's
# "{"prompt": ...}" never depends on live document parsing; the recall feed
# is fetched live at cold start (5s timeout, captured fallback) unless
# GUARDIAN_LIVE_RECALL=0.
_recall_item, _recall_mode = get_recall_item(attempt_live=os.environ.get("GUARDIAN_LIVE_RECALL", "1") == "1")
_guardian_tools = build_guardian_tools(
    _store,
    extraction_client=RecordedResponseClient(),
    extraction_mode="recorded",
    model_id=BEDROCK_MODEL_ID,
    recall_item=_recall_item,
    recall_mode=_recall_mode,
    receipts_loader=lambda: json.loads(RECEIPTS_PATH.read_text()),
    prior_bulletin_months=PRIOR_CAPTURED_MONTH,
    draft_agent=_agent,
)
_guardian_model = build_guardian_model(BEDROCK_MODEL_ID)


def _draft_dict(draft: DraftResult | None) -> dict | None:
    if draft is None:
        return None
    return {
        "subject": draft.subject,
        "body": draft.body,
        "used_llm_personalization": draft.used_llm_personalization,
    }


@app.entrypoint
def invoke(payload: dict | None) -> dict:
    payload = payload or {}
    clock_id = payload.get("clock_id", "demo-clock")
    event_id = payload.get("event_id", "demo-event")

    if "prompt" in payload:
        names = tool_names(_guardian_tools)
        if _guardian_model is None:
            return {
                "path": "agent",
                "answer": None,
                "tools_called": [],
                "tools": names,
                "error": "no model: this environment has no AWS credentials for Bedrock",
            }
        result = ask_guardian(_guardian_model, _guardian_tools, str(payload["prompt"]))
        return {
            "path": "agent",
            "question": str(payload["prompt"]),
            "answer": result.answer,
            "tools_called": result.tools_called,
            "trace": result.trace_dicts(),
            "tools": names,
            "error": result.error,
        }

    if "fields" in payload:
        result = run_discrepancy_check(
            _store, clock_id=clock_id, event_id=event_id, fields=payload["fields"], agent=_agent
        )
        return {
            "path": "fields",
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason},
            "draft": _draft_dict(result.draft),
        }

    if payload.get("extraction") == "live":
        client, mode = build_extraction_client()
    else:
        client, mode = RecordedResponseClient(), "recorded"

    result = run_sample_case(
        _store,
        clock_id=clock_id,
        event_id=event_id,
        client=client,
        mode=mode,
        model_id=BEDROCK_MODEL_ID,
        agent=_agent,
    )
    return {
        "path": "sample_case",
        "extraction_mode": result.extraction.mode,
        "needs_review": result.extraction.needs_review,
        "fields": result.extraction.fields,
        "error": result.error,
        "alert": {"decision": result.alert.decision, "reason": result.alert.reason} if result.alert else None,
        "draft": _draft_dict(result.draft),
    }


if __name__ == "__main__":
    app.run()
