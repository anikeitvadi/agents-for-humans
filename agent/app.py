"""FastAPI backend for the local demo. No AgentCore dependency — this is
the "local-first" surface from the plan; AgentCore Runtime deployment
wraps the same pipeline functions later (deploy/agentcore_entrypoint.py)
without changing any of this logic.
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from strands.models import Model

from agent.config import BEDROCK_MODEL_ID
from agent.engine.decision_gate import GateInputs, evaluate_gate
from agent.engine.store import Store
from agent.llm.document_client import build_extraction_client
from agent.llm.draft import build_bedrock_agent
from agent.llm.guardian import ask_guardian, build_guardian_model, build_guardian_tools, tool_names
from agent.packs.immigration.bulletin import PRIOR_CAPTURED_MONTH, load_seeded_case, run_bulletin_poll
from agent.packs.immigration.pipeline import extract_sample_case_fields, run_sample_case
from agent.packs.recalls.feed import get_recall_item
from agent.packs.recalls.pipeline import run_recall_check

REPO_ROOT = Path(__file__).resolve().parent.parent
RECALLS_FIXTURES_DIR = REPO_ROOT / "fixtures" / "recalls"


def _load_receipts() -> dict:
    return json.loads((RECALLS_FIXTURES_DIR / "receipts.json").read_text())


class RecallCheckRequest(BaseModel):
    receipt: str  # "seeded" or "unmatched" — picks a fixture receipt for the demo


class BulletinPollRequest(BaseModel):
    month: str  # "2025-09" or "2025-10" — which captured bulletin month to simulate polling


class AskRequest(BaseModel):
    question: str  # free text for the guardian agent (agent/llm/guardian.py)


_PRIOR_BULLETIN_MONTH = PRIOR_CAPTURED_MONTH


def create_app(
    db_path: str = "data/demo.db",
    attempt_live_recall_feed: bool = False,
    guardian_model: Model | None = None,
    auto_guardian_model: bool = True,
) -> FastAPI:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    store = Store(db_path)
    # None when no AWS credentials are configured (e.g. this sandbox) — the
    # pipeline's deterministic core is a fully correct draft either way; a
    # real Agent only adds personalization when Bedrock is actually reachable.
    bedrock_agent = build_bedrock_agent(model_id=BEDROCK_MODEL_ID)
    # "live" only when real AWS credentials are configured; otherwise a
    # deterministic recorded replay of the same specimen images (C1) — the
    # mode is surfaced in every response below so the UI never presents a
    # recorded replay as a live parse.
    extraction_client, extraction_mode = build_extraction_client()
    # attempt_live_recall_feed defaults to False so create_app() (used
    # throughout the test suite) never makes a real network call — the
    # actual running app (bottom of this file) turns it on. Either way the
    # fetched-or-fallback recall is resolved once at startup, not per
    # request, and its mode is surfaced in every response (C4).
    recall_item, recall_mode = get_recall_item(attempt_live=attempt_live_recall_feed)
    # The conversational front door: a Strands Agent whose only tools are
    # the engine's checks, bound to this app's store and clients. Tests
    # inject a scripted model; the real app uses Bedrock when credentials
    # exist and otherwise reports the agent as unavailable.
    guardian_tools = build_guardian_tools(
        store,
        extraction_client=extraction_client,
        extraction_mode=extraction_mode,
        model_id=BEDROCK_MODEL_ID,
        recall_item=recall_item,
        recall_mode=recall_mode,
        receipts_loader=_load_receipts,
        prior_bulletin_months=_PRIOR_BULLETIN_MONTH,
        draft_agent=bedrock_agent,
    )
    if guardian_model is None and auto_guardian_model:
        guardian_model = build_guardian_model(BEDROCK_MODEL_ID)
    app = FastAPI(title="Immigration Status Guardian — demo backend")

    @app.get("/api/sample-case")
    def sample_case():
        extraction = extract_sample_case_fields(extraction_client, mode=extraction_mode, model_id=BEDROCK_MODEL_ID)
        return {
            "mode": extraction.mode,
            "fields": extraction.fields,
            "evidence": extraction.evidence,
            "statuses": extraction.statuses,
            "needs_review": extraction.needs_review,
        }

    @app.post("/api/process-sample-case")
    def process_sample_case():
        result = run_sample_case(
            store,
            clock_id="demo-clock",
            event_id="demo-event",
            client=extraction_client,
            mode=extraction_mode,
            model_id=BEDROCK_MODEL_ID,
            agent=bedrock_agent,
        )
        return {
            "mode": result.extraction.mode,
            "error": result.error,
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason} if result.alert else None,
            "draft": {"subject": result.draft.subject, "body": result.draft.body} if result.draft else None,
        }

    @app.get("/api/gate-demo")
    def gate_demo():
        """Illustrates the decision gate narration for the demo: several
        events processed, most staying silent, exactly one surfacing."""
        scenarios = [
            {"label": "discrepancy found", "material": True, "actionable": True, "window_open": True},
            {"label": "no discrepancy", "material": False, "actionable": False, "window_open": False},
            {"label": "recall, no matching receipt", "material": False, "actionable": False, "window_open": False},
        ]
        results = []
        for i, s in enumerate(scenarios):
            inputs = GateInputs(
                clock_id="gate-demo",
                event_id=f"evt-{i}",
                rule_version="v1",
                material=s["material"],
                actionable=s["actionable"],
                window_open=s["window_open"],
                prior_alerts=[],
            )
            alert = evaluate_gate(inputs)
            results.append({"label": s["label"], "decision": alert.decision, "reason": alert.reason})
        return {"results": results}

    @app.post("/api/bulletin-poll")
    def bulletin_poll(req: BulletinPollRequest):
        """Simulates the unattended scheduled poll firing for one captured
        bulletin month (C3) — no user upload involved, same shared engine/
        gate/persistence/draft path as the discrepancy check."""
        case = load_seeded_case()
        result = run_bulletin_poll(
            store,
            clock_id="bulletin-clock",
            month=req.month,
            case=case,
            agent=bedrock_agent,
            previous_month=_PRIOR_BULLETIN_MONTH.get(req.month),
        )
        return {
            "case_name": case.case_name,
            "error": result.error,
            "cutoff_status": result.cutoff.status if result.cutoff else None,
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason} if result.alert else None,
            "draft": {"subject": result.draft.subject, "body": result.draft.body} if result.draft else None,
        }

    @app.post("/api/recalls/check")
    def recalls_check(req: RecallCheckRequest):
        receipts = _load_receipts()
        receipt = receipts["seeded_receipt"] if req.receipt == "seeded" else receipts["unmatched_receipt"]
        result = run_recall_check(store, clock_id="recall-clock", recall_item=recall_item, receipt=receipt)
        return {
            "mode": recall_mode,
            "matched": result.match.matched,
            "message": result.match.message,
            "demo_scope": result.match.demo_scope,
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason},
            "draft": {"subject": result.draft.subject, "body": result.draft.body} if result.draft else None,
        }

    @app.post("/api/ask")
    def ask(req: AskRequest):
        """One question, one fresh Strands agent run; the answer can only
        come from tool results (see agent/llm/guardian.py)."""
        names = tool_names(guardian_tools)
        if guardian_model is None:
            return {
                "available": False,
                "answer": None,
                "tools_called": [],
                "tools": names,
                "error": "The guardian agent needs a Bedrock model: configure AWS credentials with model access.",
            }
        result = ask_guardian(guardian_model, guardian_tools, req.question)
        return {
            "available": True,
            "answer": result.answer,
            "tools_called": result.tools_called,
            "tools": names,
            "error": result.error,
        }

    ui_dir = REPO_ROOT / "ui"
    if ui_dir.exists():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


app = create_app(attempt_live_recall_feed=True)
