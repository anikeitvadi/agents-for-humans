"""Bundled scenarios: registry, content-addressed recorded replay, and the
recorded-mode coherence rule that keeps the default demo working."""

import json

from fastapi.testclient import TestClient

from agent.app import create_app
from agent.config import BEDROCK_MODEL_ID
from agent.engine.store import Store
from agent.llm.document_client import RecordedResponseClient
from agent.packs.immigration.pipeline import run_case_from_documents
from agent.packs.immigration.scenarios import (
    DOCUMENT_KEYS,
    SCENARIOS,
    coherent_recorded_scenario,
    get_scenario,
    known_specimen_hashes,
    recorded_responses_by_hash,
    scenario_summaries,
    sha256_bytes,
)


def _docs(name):
    scenario = get_scenario(name)
    return {key: scenario.specimen_path(key).read_bytes() for key in DOCUMENT_KEYS}


def _fake_recording(name, i94, i797, passport, passport_status="extracted"):
    """A recorded-response map keyed by the scenario's specimen hashes, the
    shape scripts/record_extraction.py writes (test-only stand-in)."""
    scenario = get_scenario(name)
    values = {
        "i94": {"admit_until": {"value": i94, "evidence": f"Admit Until Date: {i94}", "status": "extracted"}},
        "i797": {"i797_valid_until": {"value": i797, "evidence": f"Valid To: {i797}", "status": "extracted"}},
        "passport": {
            "passport_expiry": {
                "value": passport,
                "evidence": "Date of Expiration: illegible" if passport is None else f"Date of Expiration: {passport}",
                "status": passport_status,
            }
        },
    }
    return {sha256_bytes(scenario.specimen_path(key).read_bytes()): values[key] for key in DOCUMENT_KEYS}


def test_registry_has_three_scenarios_with_distinct_specimens():
    assert list(SCENARIOS) == ["discrepant", "matching", "ambiguous"]
    assert all(s.has_specimens() for s in SCENARIOS.values())
    hashes = known_specimen_hashes()
    assert len(hashes) == 9
    assert all(len(owners) == 1 for owners in hashes.values())


def test_only_recorded_scenarios_are_available_offline():
    summary = {s["name"]: s for s in scenario_summaries()}
    assert summary["discrepant"]["available_offline"] is True
    assert summary["discrepant"]["expected"] == "surfaced"
    assert summary["matching"]["expected"] == "silent"
    assert summary["ambiguous"]["expected"] == "needs_review"


def test_default_recording_is_content_addressed():
    by_hash = recorded_responses_by_hash()
    discrepant = get_scenario("discrepant")
    digest = sha256_bytes(discrepant.specimen_path("i94").read_bytes())
    assert by_hash[digest]["admit_until"]["value"] == "2026-11-03"


def test_recorded_client_matches_on_bytes_before_reference_id():
    client = RecordedResponseClient()
    i94 = get_scenario("discrepant").specimen_path("i94").read_bytes()
    response = client.converse(
        modelId="m",
        messages=[{"role": "user", "content": [{"text": "(reference id: 'i94')"}, {"image": {"format": "png", "source": {"bytes": i94}}}]}],
    )
    assert json.loads(response["output"]["message"]["content"][0]["text"])["admit_until"]["value"] == "2026-11-03"


def test_coherence_rejects_mixed_sets_and_unrecorded_scenarios():
    discrepant = {k: sha256_bytes(v) for k, v in _docs("discrepant").items()}
    assert coherent_recorded_scenario(discrepant) == "discrepant"
    mixed = dict(discrepant, passport=sha256_bytes(_docs("matching")["passport"]))
    assert coherent_recorded_scenario(mixed) is None
    matching = {k: sha256_bytes(v) for k, v in _docs("matching").items()}
    assert coherent_recorded_scenario(matching) is None  # no recording bundled yet
    assert coherent_recorded_scenario({"i94": "nope", "i797": "nope", "passport": "nope"}) is None


def test_unrecorded_scenario_is_refused_in_recorded_mode_with_a_clear_reason(tmp_path):
    result = run_case_from_documents(
        Store(str(tmp_path / "l.db")), "c", RecordedResponseClient(), "recorded", BEDROCK_MODEL_ID, _docs("matching")
    )
    assert result.alert is None
    assert result.extraction.needs_review is True
    assert "bundled synthetic" in result.error


def test_matching_scenario_stays_silent_once_recorded(tmp_path, monkeypatch):
    recording = _fake_recording("matching", "2026-12-28", "2026-12-28", "2027-11-03")
    monkeypatch.setattr(get_scenario("matching"), "recording_path", tmp_path / "rec.json", raising=True) if False else None
    scenario = get_scenario("matching")
    monkeypatch.setattr(type(scenario), "has_recording", lambda self: self.name in ("discrepant", "matching"))
    client = RecordedResponseClient(responses_by_hash=recording)

    result = run_case_from_documents(Store(str(tmp_path / "l.db")), "c", client, "recorded", BEDROCK_MODEL_ID, _docs("matching"))

    assert result.error is None
    assert result.extraction.mode == "recorded"
    assert result.alert.decision == "silent"
    assert result.draft is None


def test_ambiguous_scenario_blocks_the_rule_once_recorded(tmp_path, monkeypatch):
    recording = _fake_recording("ambiguous", "2026-11-03", "2026-12-28", None, passport_status="missing")
    scenario = get_scenario("ambiguous")
    monkeypatch.setattr(type(scenario), "has_recording", lambda self: self.name in ("discrepant", "ambiguous"))
    client = RecordedResponseClient(responses_by_hash=recording)

    result = run_case_from_documents(Store(str(tmp_path / "l.db")), "c", client, "recorded", BEDROCK_MODEL_ID, _docs("ambiguous"))

    assert result.alert is None
    assert result.extraction.needs_review is True
    assert result.extraction.statuses["passport_expiry"] == "missing"
    assert result.extraction.fields["admit_until"] == "2026-11-03"  # the readable fields still come through


def test_api_lists_scenarios_and_serves_scenario_specimens(tmp_path):
    client = TestClient(create_app(db_path=str(tmp_path / "demo.db")))

    names = [s["name"] for s in client.get("/api/scenarios").json()["scenarios"]]
    assert names == ["discrepant", "matching", "ambiguous"]

    default = client.get("/api/sample-documents/i94").content
    assert default == get_scenario("discrepant").specimen_path("i94").read_bytes()
    matching = client.get("/api/sample-documents/i94?scenario=matching").content
    assert matching == get_scenario("matching").specimen_path("i94").read_bytes()
    assert matching != default
    assert client.get("/api/sample-documents/i94?scenario=nope").status_code == 404


def test_ui_has_a_scenario_picker():
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "ui" / "index.html").read_text()
    assert 'id="scenario-select"' in html
    assert "/api/scenarios" in html
    assert "?scenario=" in html
