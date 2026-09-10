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
from agent.llm.draft import build_bedrock_agent
from agent.packs.immigration.pipeline import run_discrepancy_check
from agent.packs.recalls.rules import match_recall_to_receipt

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "sample_case"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class RecallCheckRequest(BaseModel):
    receipt: str  # "seeded" or "unmatched" — picks a fixture receipt for the demo


def create_app(db_path: str = "data/demo.db") -> FastAPI:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    store = Store(db_path)
    # None when no AWS credentials are configured (e.g. this sandbox) — the
    # pipeline's deterministic core is a fully correct draft either way; a
    # real Agent only adds personalization when Bedrock is actually reachable.
    bedrock_agent = build_bedrock_agent(model_id=BEDROCK_MODEL_ID)
    app = FastAPI(title="Immigration Status Guardian — demo backend")

    @app.get("/api/sample-case")
    def sample_case():
        return _load_json("fields.json")

    @app.post("/api/process-sample-case")
    def process_sample_case():
        fields = _load_json("fields.json")
        result = run_discrepancy_check(
            store, clock_id="demo-clock", event_id="demo-event", fields=fields, agent=bedrock_agent
        )
        return {
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason},
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
