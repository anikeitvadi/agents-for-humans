"""POST /api/ask: the guardian agent behind the web UI."""

from fastapi.testclient import TestClient

from agent.app import create_app
from agent.packs.immigration.pipeline import SPECIMENS_DIR
from tests.scripted_model import ScriptedModel

TOOLS = ["check_document_dates", "run_sample_case_check", "check_uploaded_case", "check_visa_bulletin", "check_recall"]


def _specimen_upload_files():
    return {
        "i94": ("i94.png", (SPECIMENS_DIR / "i94.png").read_bytes(), "image/png"),
        "i797": ("i797.png", (SPECIMENS_DIR / "i797.png").read_bytes(), "image/png"),
        "passport": ("passport.png", (SPECIMENS_DIR / "passport.png").read_bytes(), "image/png"),
    }


def test_ask_reports_unavailable_without_a_model(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))

    body = client.post("/api/ask", json={"question": "Do my documents disagree?"}).json()

    assert body["available"] is False
    assert body["answer"] is None
    assert body["tools"] == TOOLS
    assert "Bedrock" in body["error"]


def test_ask_runs_the_agent_with_an_injected_model(tmp_path):
    # One model, two conversations worth of scripted steps: the agent loop
    # calls stream() once for the tool-use decision and once more for the
    # follow-up text per question, and /api/ask builds a fresh Agent per
    # call but shares this same model instance across both questions below.
    model = ScriptedModel(
        [
            ("tool", "run_sample_case_check", {}),
            ("text", "One thing needs your review; a draft is ready."),
            ("tool", "run_sample_case_check", {}),
            ("text", "Nothing new."),
        ]
    )
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), guardian_model=model))

    body = client.post("/api/ask", json={"question": "Check the sample case."}).json()

    assert body["available"] is True
    assert body["tools_called"] == ["run_sample_case_check"]
    assert "draft is ready" in body["answer"]
    assert body["error"] is None
    assert body["question"] == "Check the sample case."
    assert body["trace"][0]["tool"] == "run_sample_case_check"
    assert body["trace"][0]["decision"] == "surfaced"
    assert body["trace"][0]["mode"] == "recorded"
    assert body["trace"][0]["persisted_draft"] is True

    # The agent's tool wrote to the same ledger the UI reads: asking again
    # (same running app/store/client) stays silent but keeps the draft —
    # /api/process-sample-case no longer exists, so this is exercised
    # through the same tool the first question used.
    again = client.post("/api/ask", json={"question": "Check it again."}).json()
    assert again["trace"][0]["decision"] == "silent"
    assert again["trace"][0]["persisted_draft"] is True


def test_ask_rejects_missing_question(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))
    assert client.post("/api/ask", json={}).status_code == 422


def test_ask_binds_check_uploaded_case_to_the_supplied_submission_ref(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))
    processed = client.post("/api/process-documents", files=_specimen_upload_files()).json()

    model = ScriptedModel([("tool", "check_uploaded_case", {}), ("text", "Your uploaded case needs review.")])
    app_with_model = create_app(db_path=str(tmp_path / "demo.db"), guardian_model=model)
    client_with_model = TestClient(app_with_model)

    body = client_with_model.post(
        "/api/ask", json={"question": "What about the case I just uploaded?", "submission_ref": processed["ref"]}
    ).json()

    assert body["tools_called"] == ["check_uploaded_case"]
    assert body["trace"][0]["decision"] == "surfaced"
    assert body["trace"][0]["mode"] == "recorded"


def test_ask_without_a_submission_ref_reports_no_uploaded_case_available(tmp_path):
    model = ScriptedModel([("tool", "check_uploaded_case", {}), ("text", "No uploaded case yet.")])
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), guardian_model=model))

    body = client.post("/api/ask", json={"question": "What about my uploaded case?"}).json()

    assert body["trace"][0]["status"] == "error"
    assert "No uploaded case is available" in body["trace"][0]["summary"]


def test_session_id_keeps_one_agent_across_questions(tmp_path):
    model = ScriptedModel([("tool", "run_sample_case_check", {}), ("text", "One thing needs review."), ("text", "Approve the draft when ready.")])
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), guardian_model=model))

    first = client.post("/api/ask", json={"question": "Check the sample case.", "session_id": "page-1"}).json()
    second = client.post("/api/ask", json={"question": "And then?", "session_id": "page-1"}).json()

    assert first["turn"] == 1 and second["turn"] == 2
    assert second["session_id"] == "page-1"
    assert second["tools_called"] == []
    assert len(model.calls[-1]["messages"]) >= 4  # history carried into the second turn

    fresh = client.post("/api/ask", json={"question": "Hello?", "session_id": "page-2"}).json()
    assert fresh["turn"] == 1
