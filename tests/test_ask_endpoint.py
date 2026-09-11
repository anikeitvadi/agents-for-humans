"""POST /api/ask: the guardian agent behind the web UI."""

from fastapi.testclient import TestClient

from agent.app import create_app
from tests.scripted_model import ScriptedModel

TOOLS = ["check_document_dates", "run_sample_case_check", "check_visa_bulletin", "check_recall"]


def test_ask_reports_unavailable_without_a_model(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))

    body = client.post("/api/ask", json={"question": "Do my documents disagree?"}).json()

    assert body["available"] is False
    assert body["answer"] is None
    assert body["tools"] == TOOLS
    assert "Bedrock" in body["error"]


def test_ask_runs_the_agent_with_an_injected_model(tmp_path):
    model = ScriptedModel([("tool", "run_sample_case_check", {}), ("text", "One thing needs your review; a draft is ready.")])
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), guardian_model=model))

    body = client.post("/api/ask", json={"question": "Check the sample case."}).json()

    assert body["available"] is True
    assert body["tools_called"] == ["run_sample_case_check"]
    assert "draft is ready" in body["answer"]
    assert body["error"] is None

    # The agent's tool wrote to the same ledger the UI reads: the sample case
    # is now already flagged, so the UI path stays silent and keeps the draft.
    again = client.post("/api/process-sample-case").json()
    assert again["alert"]["decision"] == "silent"
    assert again["draft"] is not None


def test_ask_rejects_missing_question(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))
    assert client.post("/api/ask", json={}).status_code == 422
