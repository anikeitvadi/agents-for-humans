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

from agent.config import BEDROCK_MODEL_ID
from agent.engine.decision_gate import GateInputs, evaluate_gate
from agent.engine.store import Store
from agent.llm.document_client import build_extraction_client
from agent.llm.draft import build_bedrock_agent
from agent.packs.immigration.bulletin import load_seeded_case, run_bulletin_poll
from agent.packs.immigration.pipeline import extract_sample_case_fields, run_sample_case
from agent.packs.recalls.rules import match_recall_to_receipt

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "sample_case"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class RecallCheckRequest(BaseModel):
    receipt: str  # "seeded" or "unmatched" — picks a fixture receipt for the demo


class BulletinPollRequest(BaseModel):
    month: str  # "2025-09" or "2025-10" — which captured bulletin month to simulate polling


# The immediately preceding captured month, keyed by month — lets the poll
# skip a same-chart-type retrogression comparison correctly (see
# fixtures/bulletins/README.md) without guessing at calendar arithmetic
# over a fixture set that may not cover every month.
_PRIOR_BULLETIN_MONTH = {"2025-10": "2025-09"}


def create_app(db_path: str = "data/demo.db") -> FastAPI:
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
        demo = _load_json("recall_demo.json")
        receipt = demo["seeded_receipt"] if req.receipt == "seeded" else demo["unmatched_receipt"]
        result = match_recall_to_receipt(demo["recall_item"], receipt)
        return {"matched": result.matched, "message": result.message, "demo_scope": result.demo_scope}

    ui_dir = REPO_ROOT / "ui"
    if ui_dir.exists():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


app = create_app()
