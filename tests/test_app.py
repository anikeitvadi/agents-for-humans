import threading
import time

from fastapi.testclient import TestClient

from agent.app import create_app
from agent.packs.immigration.pipeline import SPECIMENS_DIR


def _client(tmp_path):
    app = create_app(db_path=str(tmp_path / "demo.db"))
    return TestClient(app)


def _specimen_upload_files():
    # Simulates a user selecting the downloaded synthetic sample files —
    # the actually-selected bytes are what must flow through extraction
    # (R2), not a re-read of the fixture path independent of the upload.
    return {
        "i94": ("i94.png", (SPECIMENS_DIR / "i94.png").read_bytes(), "image/png"),
        "i797": ("i797.png", (SPECIMENS_DIR / "i797.png").read_bytes(), "image/png"),
        "passport": ("passport.png", (SPECIMENS_DIR / "passport.png").read_bytes(), "image/png"),
    }


def test_sample_document_download_endpoints_serve_the_real_specimen_bytes(tmp_path):
    client = _client(tmp_path)

    for key in ("i94", "i797", "passport"):
        response = client.get(f"/api/sample-documents/{key}")
        assert response.status_code == 200
        assert response.content == (SPECIMENS_DIR / f"{key}.png").read_bytes()


def test_sample_document_download_rejects_unknown_key(tmp_path):
    client = _client(tmp_path)

    assert client.get("/api/sample-documents/unknown").status_code == 404


def test_process_documents_returns_evidence_and_decision_from_one_extraction(tmp_path):
    client = _client(tmp_path)

    response = client.post("/api/process-documents", files=_specimen_upload_files())

    assert response.status_code == 200
    body = response.json()
    # R2: evidence and decision must come from the same extraction pass.
    assert body["fields"]["admit_until"] == "2026-11-03"
    assert body["evidence"]["admit_until"] == "Admit Until Date: 11/03/2026"
    assert body["needs_review"] is False
    assert body["mode"] == "recorded"
    assert body["error"] is None
    assert body["alert"]["decision"] == "surfaced"
    assert body["draft"] is not None
    assert "55" in body["draft"]["body"]
    # F1: the draft/approval identity is derived, not a fixed string.
    assert body["ref"]["clock_id"] == "immigration-demo-user"
    assert body["ref"]["event_id"]
    assert body["draft"]["ref"] == body["ref"]
    assert body["draft"]["approved_at"] is None


def test_reprocessing_uploaded_documents_does_not_surface_twice_but_keeps_the_draft(tmp_path):
    client = _client(tmp_path)

    first = client.post("/api/process-documents", files=_specimen_upload_files())
    second = client.post("/api/process-documents", files=_specimen_upload_files())

    assert second.json()["alert"]["decision"] == "silent"
    assert second.json()["draft"] == first.json()["draft"]
    assert second.json()["ref"] == first.json()["ref"]


def test_uploaded_documents_draft_survives_across_app_restarts(tmp_path):
    db_path = str(tmp_path / "demo.db")
    first_app_client = TestClient(create_app(db_path=db_path))
    first = first_app_client.post("/api/process-documents", files=_specimen_upload_files())

    # Simulate a process restart: a fresh app/Store pointed at the same file.
    restarted_client = TestClient(create_app(db_path=db_path))
    replayed = restarted_client.post("/api/process-documents", files=_specimen_upload_files())

    assert replayed.json()["alert"]["decision"] == "silent"
    assert replayed.json()["draft"] == first.json()["draft"]


def test_process_documents_rejects_non_png_before_any_model_call(tmp_path):
    client = _client(tmp_path)
    files = _specimen_upload_files()
    files["i94"] = ("i94.png", b"\xff\xd8\xff\xe0not-a-real-png", "image/png")

    response = client.post("/api/process-documents", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["needs_review"] is True
    assert body["alert"] is None
    assert body["draft"] is None
    assert "not a valid PNG" in body["error"]


def test_process_documents_rejects_a_truncated_png_with_a_valid_signature(tmp_path):
    client = _client(tmp_path)
    good = (SPECIMENS_DIR / "i94.png").read_bytes()
    files = _specimen_upload_files()
    files["i94"] = ("i94.png", good[: len(good) // 2], "image/png")

    response = client.post("/api/process-documents", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["needs_review"] is True
    assert body["alert"] is None
    assert "not a valid PNG" in body["error"]


def test_process_documents_rejects_files_that_are_not_the_known_specimens(tmp_path):
    # F2: recorded mode must not accept arbitrary or swapped files as if
    # they were the known bundled sample — even if they are valid PNGs.
    from PIL import Image
    import io

    other_png = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(other_png, format="PNG")
    files = _specimen_upload_files()
    files["i94"] = ("i94.png", other_png.getvalue(), "image/png")

    client = _client(tmp_path)
    response = client.post("/api/process-documents", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["needs_review"] is True
    assert body["alert"] is None
    assert body["draft"] is None
    assert "bundled synthetic sample" in body["error"]


def test_process_documents_offloads_extraction_so_a_slow_call_does_not_block_the_event_loop(tmp_path):
    # F4: a slow injected extraction call must not prevent a concurrent
    # lightweight request from completing promptly.
    class SlowClient:
        mode = "recorded"
        fallback_reason = None

        def converse(self, **kwargs):
            time.sleep(0.2)
            from agent.llm.document_client import RecordedResponseClient

            return RecordedResponseClient().converse(**kwargs)

    app = create_app(db_path=str(tmp_path / "demo.db"), extraction_client=SlowClient())
    client = TestClient(app)

    heartbeat_times = []

    def heartbeat():
        start = time.monotonic()
        client.get("/api/gate-demo")
        heartbeat_times.append(time.monotonic() - start)

    upload_thread = threading.Thread(target=lambda: client.post("/api/process-documents", files=_specimen_upload_files()))
    heartbeat_thread = threading.Thread(target=heartbeat)

    upload_thread.start()
    time.sleep(0.05)  # let the upload's slow extraction start first
    heartbeat_thread.start()
    upload_thread.join()
    heartbeat_thread.join()

    # The lightweight request must not have been stuck behind the ~0.6s
    # (3 documents x 0.2s) slow extraction on the event loop.
    assert heartbeat_times[0] < 0.5


def test_reset_during_in_flight_processing_aborts_instead_of_recreating_records(tmp_path):
    # A reset that happens while an upload is still extracting must not let
    # that upload's result land afterward — the epoch check must catch it.
    from agent.engine.store import Store

    class BlockingClient:
        mode = "recorded"
        fallback_reason = None
        release = threading.Event()

        def converse(self, **kwargs):
            BlockingClient.release.wait(timeout=2)
            from agent.llm.document_client import RecordedResponseClient

            return RecordedResponseClient().converse(**kwargs)

    db_path = str(tmp_path / "demo.db")
    app = create_app(db_path=db_path, extraction_client=BlockingClient())
    client = TestClient(app)

    result_holder = {}

    def upload():
        response = client.post("/api/process-documents", files=_specimen_upload_files())
        result_holder["body"] = response.json()

    thread = threading.Thread(target=upload)
    thread.start()
    time.sleep(0.05)  # let the upload start and capture its epoch
    client.post("/api/reset")
    BlockingClient.release.set()
    thread.join()

    assert result_holder["body"]["error"] is not None
    assert result_holder["body"]["alert"] is None

    store = Store(db_path)
    assert store.list_alerts("immigration-demo-user") == []


def test_bulletin_poll_september_stays_silent_then_october_surfaces_unattended(tmp_path):
    client = _client(tmp_path)

    september = client.post("/api/bulletin-poll", json={"month": "2025-09"})
    october = client.post("/api/bulletin-poll", json={"month": "2025-10"})

    assert september.json()["cutoff_status"] == "not_current"
    assert september.json()["alert"]["decision"] == "silent"
    assert september.json()["draft"] is None

    assert october.json()["cutoff_status"] == "current"
    assert october.json()["alert"]["decision"] == "surfaced"
    assert october.json()["draft"] is not None
    assert october.json()["priority_date"]


def test_bulletin_poll_repeat_produces_no_second_ping(tmp_path):
    client = _client(tmp_path)

    first = client.post("/api/bulletin-poll", json={"month": "2025-10"})
    second = client.post("/api/bulletin-poll", json={"month": "2025-10"})

    assert second.json()["alert"]["decision"] == "silent"
    assert second.json()["draft"] == first.json()["draft"]


def test_bulletin_poll_missing_month_produces_visible_error_not_a_crash(tmp_path):
    client = _client(tmp_path)

    response = client.post("/api/bulletin-poll", json={"month": "2099-01"})

    assert response.status_code == 200
    assert response.json()["error"] is not None
    assert response.json()["alert"] is None


def test_gate_demo_endpoint_shows_two_silent_one_surfaced(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/gate-demo")

    body = response.json()
    decisions = [item["decision"] for item in body["results"]]
    assert decisions.count("surfaced") == 1
    assert decisions.count("silent") == 2
    # Product polish: the gate illustration must not reference the recall
    # pack now that the recall demo isn't in the UI.
    labels = " ".join(item["label"] for item in body["results"])
    assert "recall" not in labels.lower()


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
