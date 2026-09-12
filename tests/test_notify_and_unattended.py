"""Outbound pings never raise, and the Runtime's unattended bulletin check
pings exactly when the gate surfaces."""

import importlib
import json

import pytest

from agent.notify import PingResult, publish_sns, send_email

pytest.importorskip("bedrock_agentcore")


class FakeSns:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def publish(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("AuthorizationError: not authorized to publish")
        return {"MessageId": "msg-123"}


class FakeSes:
    def __init__(self):
        self.calls = []

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        return {"MessageId": "ses-456"}


def test_publish_sns_reports_success_and_failure_without_raising():
    ok = publish_sns("arn:aws:sns:us-east-1:1:t", "subject", "body", client=FakeSns())
    assert ok == PingResult(sent=True, channel="sns", target="arn:aws:sns:us-east-1:1:t", message_id="msg-123")

    failed = publish_sns("arn:aws:sns:us-east-1:1:t", "subject", "body", client=FakeSns(fail=True))
    assert failed.sent is False
    assert "AuthorizationError" in failed.error


def test_send_email_uses_ses_and_reports_the_recipient():
    ses = FakeSes()
    result = send_email("guardian@example.com", "attorney@example.com", "Subject", "Body", client=ses)
    assert result.sent is True and result.channel == "ses" and result.target == "attorney@example.com"
    assert ses.calls[0]["Destination"] == {"ToAddresses": ["attorney@example.com"]}


def _load_entrypoint(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "ledger.db"))
    monkeypatch.setenv("GUARDIAN_LIVE_RECALL", "0")
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no-credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-config"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    return importlib.reload(importlib.import_module("deploy.agentcore_entrypoint"))


def test_unattended_check_pings_only_when_the_gate_surfaces(monkeypatch, tmp_path):
    entrypoint = _load_entrypoint(monkeypatch, tmp_path)
    published = []
    monkeypatch.setattr(entrypoint, "publish_sns", lambda topic, subject, body: (published.append((topic, subject, body)) or PingResult(True, "sns", topic, "m1")))

    september = entrypoint.invoke({"check": "bulletin", "month": "2025-09", "notify_topic_arn": "arn:t"})
    assert september["path"] == "bulletin"
    assert september["alert"]["decision"] == "silent"
    assert september["notified"] is False and september["notification"] is None
    assert published == []

    october = entrypoint.invoke({"check": "bulletin", "month": "2025-10", "notify_topic_arn": "arn:t"})
    assert october["alert"]["decision"] == "surfaced"
    assert october["notified"] is True
    assert october["notification"]["message_id"] == "m1"
    assert published[0][0] == "arn:t"
    assert "EB2-India" in published[0][1]
    assert "not legal advice" in published[0][2]

    # Same month again: silent, no second ping, draft still returned.
    again = entrypoint.invoke({"check": "bulletin", "month": "2025-10", "notify_topic_arn": "arn:t"})
    assert again["alert"]["decision"] == "silent"
    assert again["notified"] is False
    assert again["draft"] is not None
    assert len(published) == 1


def test_unattended_check_without_a_topic_surfaces_but_does_not_ping(monkeypatch, tmp_path):
    entrypoint = _load_entrypoint(monkeypatch, tmp_path)
    monkeypatch.delenv("GUARDIAN_SNS_TOPIC_ARN", raising=False)
    out = entrypoint.invoke({"check": "bulletin", "month": "2025-10"})
    assert out["alert"]["decision"] == "surfaced"
    assert out["notified"] is False and out["topic_arn"] is None


def test_lambda_builds_the_scheduled_payload(monkeypatch):
    monkeypatch.setenv("TOPIC_ARN", "arn:aws:sns:us-east-1:1:t")
    monkeypatch.setenv("MONTH", "2025-09")
    lambda_module = importlib.import_module("deploy.unattended.lambda_function")
    assert lambda_module.build_payload(None) == {"check": "bulletin", "month": "2025-09", "notify_topic_arn": "arn:aws:sns:us-east-1:1:t"}
    assert lambda_module.build_payload({"month": "2025-10"})["month"] == "2025-10"
