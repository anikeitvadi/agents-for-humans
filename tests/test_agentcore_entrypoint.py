"""deploy/agentcore_entrypoint.py wraps the same pipeline as the web app.
Runs offline: credentials are hidden so the draft uses its deterministic
core and extraction replays the recorded response."""

import importlib

import pytest

pytest.importorskip("bedrock_agentcore")


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_DB_PATH", str(tmp_path / "ledger.db"))
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no-credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-config"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("GUARDIAN_LIVE_RECALL", "0")
    module = importlib.import_module("deploy.agentcore_entrypoint")
    return importlib.reload(module)


def test_empty_payload_runs_recorded_sample_case_and_dedups_on_repeat(monkeypatch, tmp_path):
    entrypoint = _load(monkeypatch, tmp_path)

    first = entrypoint.invoke({})
    assert first["path"] == "sample_case"
    assert first["extraction_mode"] == "recorded"
    assert first["error"] is None
    assert first["alert"]["decision"] == "surfaced"
    assert "55" in first["draft"]["body"]
    assert first["draft"]["used_llm_personalization"] is False

    second = entrypoint.invoke({})
    assert second["alert"]["decision"] == "silent"
    assert second["draft"]["body"] == first["draft"]["body"]


def test_fields_payload_skips_extraction(monkeypatch, tmp_path):
    entrypoint = _load(monkeypatch, tmp_path)

    out = entrypoint.invoke(
        {
            "event_id": "evt-fields",
            "fields": {"admit_until": "2026-11-03", "i797_valid_until": "2026-12-28", "case_name": "T"},
        }
    )
    assert out["path"] == "fields"
    assert out["alert"]["decision"] == "surfaced"
    assert "55" in out["draft"]["body"]


def test_none_payload_is_treated_as_empty(monkeypatch, tmp_path):
    entrypoint = _load(monkeypatch, tmp_path)
    assert entrypoint.invoke(None)["path"] == "sample_case"


def test_prompt_payload_reports_missing_model_offline(monkeypatch, tmp_path):
    entrypoint = _load(monkeypatch, tmp_path)

    out = entrypoint.invoke({"prompt": "Do my documents disagree?"})

    assert out["path"] == "agent"
    assert out["answer"] is None
    assert out["tools"] == ["check_document_dates", "run_sample_case_check", "check_visa_bulletin", "check_recall"]
    assert "model" in out["error"]
