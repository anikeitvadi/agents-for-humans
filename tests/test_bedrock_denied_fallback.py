"""Regression: credentials present but Bedrock denied (the account-level
"Error 002" seen on 2026-09-11) must transparently fall back to the recorded
replay, label it truthfully, and never turn a button into a silent 500."""

from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from agent.app import create_app
from agent.llm.document_client import FailoverExtractionClient, RecordedResponseClient
from agent.packs.immigration.pipeline import SPECIMENS_DIR


def _specimen_upload_files():
    return {
        "i94": ("i94.png", (SPECIMENS_DIR / "i94.png").read_bytes(), "image/png"),
        "i797": ("i797.png", (SPECIMENS_DIR / "i797.png").read_bytes(), "image/png"),
        "passport": ("passport.png", (SPECIMENS_DIR / "passport.png").read_bytes(), "image/png"),
    }


class DeniedBedrockClient:
    """Looks like a live bedrock-runtime client whose account is blocked."""

    calls = 0

    def converse(self, **kwargs):
        DeniedBedrockClient.calls += 1
        raise ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Error 002: Access to Bedrock models is not allowed for this account"}},
            "Converse",
        )


class LiveOkClient:
    def __init__(self):
        self._recorded = RecordedResponseClient()

    def converse(self, **kwargs):
        return self._recorded.converse(**kwargs)


def _reference_id_request(document_name: str) -> dict:
    # extract.py (R1) sends the reference id in the prompt text, not a
    # `document` block name — the recorded client's matcher looks there.
    return {"messages": [{"role": "user", "content": [{"text": f"...reference id: '{document_name}'..."}]}]}


def test_failover_client_falls_back_once_and_reports_why():
    client = FailoverExtractionClient(DeniedBedrockClient())
    assert client.mode == "live"  # credentials present: intent is live, not yet proven

    request = _reference_id_request("i94")
    response = client.converse(**request)

    assert "content" in response["output"]["message"]
    assert client.mode == "recorded"
    assert "Error 002" in client.fallback_reason
    before = DeniedBedrockClient.calls
    client.converse(**request)
    assert DeniedBedrockClient.calls == before  # sticky: no repeated failing round-trips


def test_failover_client_stays_live_when_live_works():
    client = FailoverExtractionClient(LiveOkClient())
    client.converse(**_reference_id_request("i94"))
    assert client.mode == "live"
    assert client.fallback_reason is None


def test_failover_client_without_credentials_is_recorded_from_the_start():
    client = FailoverExtractionClient(None)
    assert client.mode == "recorded"
    assert "no AWS credentials" in client.fallback_reason


def test_upload_flow_degrades_to_recorded_when_bedrock_is_denied(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), extraction_client=DeniedBedrockClient()))

    processed = client.post("/api/process-documents", files=_specimen_upload_files())
    assert processed.status_code == 200
    body = processed.json()
    assert body["mode"] == "recorded"
    assert "Error 002" in body["mode_reason"]
    assert body["fields"]["admit_until"] == "2026-11-03"
    assert body["needs_review"] is False
    assert body["error"] is None
    assert body["alert"]["decision"] == "surfaced"
    assert "55" in body["draft"]["body"]
    assert body["draft"]["used_llm_personalization"] is False


def test_recorded_mode_is_never_reported_as_live_after_a_fallback(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), extraction_client=DeniedBedrockClient()))
    first = client.post("/api/process-documents", files=_specimen_upload_files()).json()
    second = client.post("/api/process-documents", files=_specimen_upload_files()).json()
    assert first["mode"] == second["mode"] == "recorded"


def test_unexpected_server_errors_are_json_not_text(tmp_path, monkeypatch):
    # R3 already turns a Converse failure into a controlled needs_review
    # result (see test_partial_live_failure... below and test_extraction.py),
    # so this exercises the invariant one layer up: a genuinely unexpected
    # exception anywhere else in the request (here, the ledger write) must
    # still surface as JSON, never a bare-text 500.
    from agent.engine.store import Store

    def _boom(self, *args, **kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(Store, "save_event", _boom)

    app = create_app(db_path=str(tmp_path / "demo.db"))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/process-documents", files=_specimen_upload_files())

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert "ledger unavailable" in response.json()["error"]


def test_partial_live_failure_mid_batch_returns_a_controlled_error_not_a_mixed_result(tmp_path):
    # A client that succeeds live on the first document then fails on the
    # second must not produce a result mixing a genuine live field with
    # recorded ones under a single "recorded" label.
    class FailsAfterFirstCall:
        calls = 0

        def converse(self, **kwargs):
            FailsAfterFirstCall.calls += 1
            if FailsAfterFirstCall.calls == 1:
                return RecordedResponseClient().converse(**kwargs)
            raise RuntimeError("simulated mid-batch failure")

    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), extraction_client=FailsAfterFirstCall()))

    response = client.post("/api/process-documents", files=_specimen_upload_files())

    assert response.status_code == 200
    body = response.json()
    assert body["needs_review"] is True
    assert body["alert"] is None
    assert body["draft"] is None
    assert "partway through" in body["error"]
