"""Public-demo guards (synthetic uploads only, request caps, config flags)
and the optional SES delivery on approval."""

from fastapi.testclient import TestClient

from agent.app import _RateLimiter, create_app
from agent.packs.immigration.scenarios import get_scenario


def _files(scenario="discrepant", **overrides):
    s = get_scenario(scenario)
    files = {key: (f"{key}.png", s.specimen_path(key).read_bytes(), "image/png") for key in ("i94", "i797", "passport")}
    files.update(overrides)
    return files


class FakeSes:
    def __init__(self):
        self.calls = []

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        return {"MessageId": "ses-1"}


def test_config_reports_capabilities_truthfully(tmp_path, monkeypatch):
    monkeypatch.delenv("GUARDIAN_SES_SENDER", raising=False)
    local = TestClient(create_app(db_path=str(tmp_path / "a.db"), public_demo=False)).get("/api/config").json()
    assert local == {"public_demo": False, "email_enabled": False, "notice": None}

    monkeypatch.setenv("GUARDIAN_SES_SENDER", "guardian@example.com")
    public = TestClient(create_app(db_path=str(tmp_path / "b.db"), public_demo=True)).get("/api/config").json()
    assert public["public_demo"] is True and public["email_enabled"] is True
    assert "synthetic" in public["notice"]


def test_public_demo_rejects_non_bundled_uploads_but_accepts_bundled_ones(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), public_demo=True))

    ok = client.post("/api/process-documents", files=_files())
    assert ok.status_code == 200 and ok.json()["alert"]["decision"] == "surfaced"

    tampered = _files(passport=("passport.png", get_scenario("discrepant").specimen_path("passport").read_bytes() + b"\n", "image/png"))
    rejected = client.post("/api/process-documents", files=tampered)
    assert rejected.status_code == 400
    assert "bundled synthetic" in rejected.json()["error"]


def test_local_runs_are_not_restricted_to_bundled_uploads(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), public_demo=False))
    tampered = _files(passport=("passport.png", get_scenario("discrepant").specimen_path("passport").read_bytes() + b"\n", "image/png"))
    response = client.post("/api/process-documents", files=tampered)
    assert response.status_code == 200  # recorded mode refuses it with a reason, but it is not a policy rejection
    assert "bundled synthetic" in response.json()["error"]


def test_rate_limiter_caps_per_client_window():
    limiter = _RateLimiter(limit=3, window=60.0)
    assert [limiter.allow("a", now=t) for t in (0, 1, 2)] == [True, True, True]
    assert limiter.allow("a", now=3) is False
    assert limiter.allow("b", now=3) is True
    assert limiter.allow("a", now=61.5) is True


def test_public_demo_returns_429_when_a_client_exceeds_the_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_RATE_LIMIT", "2")
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), public_demo=True))
    assert client.get("/api/scenarios").status_code == 200
    assert client.get("/api/scenarios").status_code == 200
    third = client.get("/api/scenarios")
    assert third.status_code == 429
    assert "Too many requests" in third.json()["error"]


def test_approval_sends_via_ses_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_SES_SENDER", "guardian@example.com")
    ses = FakeSes()
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db"), ses_client=ses))
    ref = client.post("/api/process-documents", files=_files()).json()["draft"]["ref"]

    body = client.post("/api/drafts/approve", json={**ref, "send_to": "attorney@example.com"}).json()

    assert body["approved"] is True
    assert body["state"] == "Approved and sent to attorney@example.com"
    assert body["delivery"]["sent"] is True and body["delivery"]["message_id"] == "ses-1"
    assert ses.calls[0]["Destination"] == {"ToAddresses": ["attorney@example.com"]}
    assert "55 day" in ses.calls[0]["Content"]["Simple"]["Body"]["Text"]["Data"]


def test_approval_without_email_configured_never_claims_a_send(tmp_path, monkeypatch):
    monkeypatch.delenv("GUARDIAN_SES_SENDER", raising=False)
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))
    ref = client.post("/api/process-documents", files=_files()).json()["draft"]["ref"]

    plain = client.post("/api/drafts/approve", json=ref).json()
    assert plain["state"] == "Approved and ready to send" and plain["delivery"] is None

    asked = client.post("/api/drafts/approve", json={**ref, "send_to": "attorney@example.com"}).json()
    assert asked["state"] == "Approved and ready to send"
    assert asked["delivery"]["sent"] is False and "not configured" in asked["delivery"]["error"]
