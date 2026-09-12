"""Approve for attorney review: an idempotent, persisted action receipt."""

from fastapi.testclient import TestClient

from agent.app import APPROVE_ACTION, create_app
from agent.engine.store import Store
from agent.packs.immigration.pipeline import SPECIMENS_DIR


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


def _specimen_upload_files():
    return {
        "i94": ("i94.png", (SPECIMENS_DIR / "i94.png").read_bytes(), "image/png"),
        "i797": ("i797.png", (SPECIMENS_DIR / "i797.png").read_bytes(), "image/png"),
        "passport": ("passport.png", (SPECIMENS_DIR / "passport.png").read_bytes(), "image/png"),
    }


def test_drafts_carry_their_ledger_key_and_approval_state(tmp_path):
    client = _client(tmp_path)

    draft = client.post("/api/process-documents", files=_specimen_upload_files()).json()["draft"]

    assert draft["kind"] == "attorney_review"
    assert draft["ref"]["clock_id"] == "immigration-demo-user"
    assert draft["ref"]["event_id"]
    assert draft["ref"]["rule_version"] == "v1"
    assert draft["approved_at"] is None


def test_approve_records_receipt_and_repeat_is_a_no_op(tmp_path):
    client = _client(tmp_path)
    ref = client.post("/api/process-documents", files=_specimen_upload_files()).json()["draft"]["ref"]

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
    draft = client.post("/api/process-documents", files=_specimen_upload_files()).json()["draft"]
    assert draft["approved_at"] == body["receipt"]["created_at"]


def test_a_different_submission_does_not_inherit_an_earlier_approval(tmp_path):
    # F1 / identity: uploading a different case (via an injected extractor,
    # since the bundled-sample recorded path only ever verifies to the one
    # known specimen set) must get its own draft, never inherit another
    # submission's draft or approval receipt.
    from agent.llm.document_client import RecordedResponseClient

    client = _client(tmp_path)
    first = client.post("/api/process-documents", files=_specimen_upload_files()).json()
    client.post("/api/drafts/approve", json=first["draft"]["ref"])

    different_responses = {
        "i94": {"admit_until": {"value": "2027-01-01", "evidence": "Admit Until Date: 01/01/2027", "status": "extracted"}},
        "i797": {"i797_valid_until": {"value": "2027-04-01", "evidence": "Valid To: 04/01/2027", "status": "extracted"}},
        "passport": {"passport_expiry": {"value": "2030-01-01", "evidence": "Expiration: 01/01/2030", "status": "extracted"}},
    }
    app = create_app(db_path=str(tmp_path / "demo.db"), extraction_client=RecordedResponseClient(responses=different_responses))
    # Reuse the same on-disk ledger the first app used, but a client whose
    # recorded responses (and therefore identity) differ from submission A.
    other_client = TestClient(app)
    second = other_client.post("/api/process-documents", files=_specimen_upload_files()).json()

    assert second["ref"]["event_id"] != first["ref"]["event_id"]
    assert second["draft"]["approved_at"] is None
    assert second["draft"] != first["draft"]


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
