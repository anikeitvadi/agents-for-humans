"""Regression: credentials present but Bedrock denied (the account-level
"Error 002" seen on 2026-09-11) must transparently fall back to the recorded
replay, label it truthfully, and never turn a button into a silent 500."""

from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from agent.app import create_app
from agent.llm.document_client import FailoverExtractionClient, RecordedResponseClient


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


def test_failover_client_falls_back_once_and_reports_why():
    client = FailoverExtractionClient(DeniedBedrockClient())
    assert client.mode == "live"  # credentials present: intent is live, not yet proven

    request = {"messages": [{"role": "user", "content": [{"document": {"name": "i94"}}]}]}
    response = client.converse(**request)

    assert "content" in response["output"]["message"]
    assert client.mode == "recorded"
    assert "Error 002" in client.fallback_reason
    before = DeniedBedrockClient.calls
    client.converse(**request)
    assert DeniedBedrockClient.calls == before  # sticky: no repeated failing round-trips


def test_failover_client_stays_live_when_live_works():
    client = FailoverExtractionClient(LiveOkClient())
    client.converse(messages=[{"role": "user", "content": [{"document": {"name": "i94"}}]}])
    assert client.mode == "live"
    assert client.fallback_reason is None


def test_failover_client_without_credentials_is_recorded_from_the_start():
    client = FailoverExtractionClient(None)
    assert client.mode == "recorded"
    assert "no AWS credentials" in client.fallback_reason


def test_sample_case_endpoints_degrade_to_recorded_when_bedrock_is_denied(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), extraction_client=DeniedBedrockClient()))

    fields = client.get("/api/sample-case")
    assert fields.status_code == 200
    body = fields.json()
    assert body["mode"] == "recorded"
    assert "Error 002" in body["mode_reason"]
    assert body["fields"]["admit_until"] == "2026-11-03"
    assert body["needs_review"] is False

    processed = client.post("/api/process-sample-case")
    assert processed.status_code == 200
    body = processed.json()
    assert body["mode"] == "recorded"
    assert "Error 002" in body["mode_reason"]
    assert body["error"] is None
    assert body["alert"]["decision"] == "surfaced"
    assert "55" in body["draft"]["body"]
    assert body["draft"]["used_llm_personalization"] is False


def test_recorded_mode_is_never_reported_as_live_after_a_fallback(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), extraction_client=DeniedBedrockClient()))
    first = client.get("/api/sample-case").json()
    second = client.get("/api/sample-case").json()
    assert first["mode"] == second["mode"] == "recorded"


def test_unexpected_server_errors_are_json_not_text(tmp_path):
    class Exploding:
        def converse(self, **kwargs):
            raise RuntimeError("boom")

    class ExplodingRecorded(RecordedResponseClient):
        def converse(self, **kwargs):
            raise RuntimeError("fixture missing")

    failover = FailoverExtractionClient(Exploding(), recorded_client=ExplodingRecorded())
    app = create_app(db_path=str(tmp_path / "demo.db"), extraction_client=failover)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/sample-case")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert "fixture missing" in response.json()["error"]
