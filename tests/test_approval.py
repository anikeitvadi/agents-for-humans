"""Approve for attorney review: an idempotent, persisted action receipt."""

from fastapi.testclient import TestClient

from agent.app import APPROVE_ACTION, create_app
from agent.engine.store import Store


def test_record_action_is_idempotent_and_survives_restart(tmp_path):
    db = str(tmp_path / "ledger.db")
    store = Store(db)

    first = store.record_action("c1", "e1", "v1", APPROVE_ACTION)
    second = store.record_action("c1", "e1", "v1", APPROVE_ACTION)

    assert first.already_recorded is False
    assert second.already_recorded is True
    assert second.created_at == first.created_at

    reopened = Store(db).get_action("c1", "e1", "v1", APPROVE_ACTION)
    assert reopened is not None
    assert reopened.created_at == first.created_at
    assert Store(db).get_action("c1", "other", "v1", APPROVE_ACTION) is None


def _client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "demo.db")))


def test_drafts_carry_their_ledger_key_and_approval_state(tmp_path):
    client = _client(tmp_path)

    draft = client.post("/api/process-sample-case").json()["draft"]

    assert draft["kind"] == "attorney_review"
    assert draft["ref"] == {"clock_id": "demo-clock", "event_id": "demo-event", "rule_version": "v1"}
    assert draft["approved_at"] is None


def test_approve_records_receipt_and_repeat_is_a_no_op(tmp_path):
    client = _client(tmp_path)
    ref = client.post("/api/process-sample-case").json()["draft"]["ref"]

    first = client.post("/api/drafts/approve", json=ref)
    assert first.status_code == 200
    body = first.json()
    assert body["approved"] is True
    assert body["already_approved"] is False
    assert body["state"] == "Approved and ready to send"
    assert body["receipt"]["action_type"] == APPROVE_ACTION
    assert body["receipt"]["created_at"]

    again = client.post("/api/drafts/approve", json=ref).json()
    assert again["already_approved"] is True
    assert again["receipt"]["created_at"] == body["receipt"]["created_at"]

    # The approval shows up on the draft itself on the next (silent) check.
    draft = client.post("/api/process-sample-case").json()["draft"]
    assert draft["approved_at"] == body["receipt"]["created_at"]


def test_approve_unknown_draft_is_a_json_404(tmp_path):
    client = _client(tmp_path)
    response = client.post("/api/drafts/approve", json={"clock_id": "x", "event_id": "y", "rule_version": "v1"})
    assert response.status_code == 404
    assert "No ready draft" in response.json()["error"]


def test_bulletin_and_recall_drafts_are_approvable_with_the_right_kind(tmp_path):
    client = _client(tmp_path)

    bulletin = client.post("/api/bulletin-poll", json={"month": "2025-10"}).json()["draft"]
    assert bulletin["kind"] == "attorney_review"
    assert client.post("/api/drafts/approve", json=bulletin["ref"]).status_code == 200

    recall = client.post("/api/recalls/check", json={"receipt": "seeded"}).json()["draft"]
    assert recall["kind"] == "recall_remedy"
    assert recall["ref"]["clock_id"] == "recall-clock"
