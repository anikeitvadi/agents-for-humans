"""POST /api/reset clears the ledger so a demo can be replayed from the top."""

from fastapi.testclient import TestClient

from agent.app import create_app


def test_reset_makes_the_sample_case_surface_again_and_clears_approvals(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))

    first = client.post("/api/process-sample-case").json()
    assert first["alert"]["decision"] == "surfaced"
    client.post("/api/drafts/approve", json=first["draft"]["ref"])
    assert client.post("/api/process-sample-case").json()["alert"]["decision"] == "silent"

    assert client.post("/api/reset").json() == {"reset": True}

    again = client.post("/api/process-sample-case").json()
    assert again["alert"]["decision"] == "surfaced"
    assert again["draft"]["approved_at"] is None
