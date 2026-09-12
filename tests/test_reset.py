"""POST /api/reset clears the ledger so a demo can be replayed from the top."""

from fastapi.testclient import TestClient

from agent.app import create_app
from agent.packs.immigration.pipeline import SPECIMENS_DIR


def _specimen_upload_files():
    return {
        "i94": ("i94.png", (SPECIMENS_DIR / "i94.png").read_bytes(), "image/png"),
        "i797": ("i797.png", (SPECIMENS_DIR / "i797.png").read_bytes(), "image/png"),
        "passport": ("passport.png", (SPECIMENS_DIR / "passport.png").read_bytes(), "image/png"),
    }


def test_reset_makes_the_case_surface_again_and_clears_approvals(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))

    first = client.post("/api/process-documents", files=_specimen_upload_files()).json()
    assert first["alert"]["decision"] == "surfaced"
    client.post("/api/drafts/approve", json=first["draft"]["ref"])
    assert client.post("/api/process-documents", files=_specimen_upload_files()).json()["alert"]["decision"] == "silent"

    assert client.post("/api/reset").json() == {"reset": True}

    again = client.post("/api/process-documents", files=_specimen_upload_files()).json()
    assert again["alert"]["decision"] == "surfaced"
    assert again["draft"]["approved_at"] is None
    # Same documents processed the same way -> same derived identity.
    assert again["ref"]["event_id"] == first["ref"]["event_id"]
