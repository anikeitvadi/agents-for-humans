from fastapi.testclient import TestClient

from agent.app import create_app


def _client(tmp_path):
    app = create_app(db_path=str(tmp_path / "demo.db"))
    return TestClient(app)


def test_sample_case_endpoint_returns_fields_with_evidence(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/sample-case")

    assert response.status_code == 200
    body = response.json()
    assert body["admit_until"] == "2026-11-03"
    assert "evidence" in body


def test_process_sample_case_surfaces_discrepancy_with_draft(tmp_path):
    client = _client(tmp_path)

    response = client.post("/api/process-sample-case")

    assert response.status_code == 200
    body = response.json()
    assert body["alert"]["decision"] == "surfaced"
    assert body["draft"] is not None
    assert "55" in body["draft"]["body"]


def test_reprocessing_sample_case_does_not_surface_twice(tmp_path):
    client = _client(tmp_path)

    client.post("/api/process-sample-case")
    second = client.post("/api/process-sample-case")

    assert second.json()["alert"]["decision"] == "silent"
    assert second.json()["draft"] is None


def test_gate_demo_endpoint_shows_two_silent_one_surfaced(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/gate-demo")

    body = response.json()
    decisions = [item["decision"] for item in body["results"]]
    assert decisions.count("surfaced") == 1
    assert decisions.count("silent") == 2


def test_recall_demo_matched_receipt_pings_once(tmp_path):
    client = _client(tmp_path)

    response = client.post("/api/recalls/check", json={"receipt": "seeded"})

    body = response.json()
    assert body["matched"] is True
    assert "218" in body["message"]


def test_recall_demo_unmatched_receipt_produces_no_false_ping(tmp_path):
    client = _client(tmp_path)

    response = client.post("/api/recalls/check", json={"receipt": "unmatched"})

    body = response.json()
    assert body["matched"] is False
