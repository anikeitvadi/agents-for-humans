"""Bundled sample scenarios for the demo.

Each scenario is a coherent set of three synthetic documents (I-94, I-797,
passport) with an expected outcome, so the demo can show the engine both
pinging and staying quiet on the primary flow, and refusing to run the rule
when a field is unreadable:

  discrepant  CBP cut the I-94 to passport expiry: 55-day gap  -> surfaced
  matching    I-94 and I-797 agree                              -> silent
  ambiguous   passport expiry is unreadable                     -> needs_review

Recorded Bedrock responses live next to each scenario's specimens
(`recorded_extraction_response.json`, produced by scripts/record_extraction.py
against live Bedrock). A scenario without a recording is only usable with
live Bedrock; the UI says so. Recorded mode identifies a document by the
sha256 of its bytes, so a swapped or edited file never gets another file's
replay.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "sample_case"
DOCUMENT_KEYS = ("i94", "i797", "passport")


@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    description: str
    expected: str  # "surfaced" | "silent" | "needs_review"
    specimens_dir: Path
    recording_path: Path

    def specimen_path(self, key: str) -> Path:
        return self.specimens_dir / f"{key}.png"

    def has_specimens(self) -> bool:
        return all(self.specimen_path(key).exists() for key in DOCUMENT_KEYS)

    def has_recording(self) -> bool:
        return self.recording_path.exists()


SCENARIOS: dict[str, Scenario] = {
    "discrepant": Scenario(
        name="discrepant",
        title="I-94 cut to passport expiry (55-day gap)",
        description="CBP admitted the traveler only until the passport expires, 55 days before the I-797 validity end. One ping, one draft.",
        expected="surfaced",
        specimens_dir=FIXTURES_DIR / "specimens",
        recording_path=FIXTURES_DIR / "recorded_extraction_response.json",
    ),
    "matching": Scenario(
        name="matching",
        title="Dates agree",
        description="The I-94 admit-until date matches the I-797 validity end. Nothing to flag: the engine stays silent on the primary flow, not just on repeats.",
        expected="silent",
        specimens_dir=FIXTURES_DIR / "scenarios" / "matching",
        recording_path=FIXTURES_DIR / "scenarios" / "matching" / "recorded_extraction_response.json",
    ),
    "ambiguous": Scenario(
        name="ambiguous",
        title="Passport expiry unreadable",
        description="The passport's expiration line is smudged. Extraction reports the field as missing, and the rule refuses to run on a guess.",
        expected="needs_review",
        specimens_dir=FIXTURES_DIR / "scenarios" / "ambiguous",
        recording_path=FIXTURES_DIR / "scenarios" / "ambiguous" / "recorded_extraction_response.json",
    ),
}


def get_scenario(name: str) -> Scenario:
    try:
        return SCENARIOS[name]
    except KeyError:
        raise ValueError(f"unknown scenario '{name}'; choose one of {', '.join(SCENARIOS)}") from None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def known_specimen_hashes() -> dict[str, set[tuple[str, str]]]:
    """sha256 of every bundled specimen -> {(scenario name, document key)}.
    Set-valued so two scenarios that happen to share an identical file
    never shadow each other."""
    known: dict[str, set[tuple[str, str]]] = {}
    for scenario in SCENARIOS.values():
        if not scenario.has_specimens():
            continue
        for key in DOCUMENT_KEYS:
            known.setdefault(sha256_bytes(scenario.specimen_path(key).read_bytes()), set()).add((scenario.name, key))
    return known


def coherent_recorded_scenario(provenance: dict[str, str]) -> str | None:
    """The one bundled scenario (with a recording) whose specimens exactly
    match the uploaded hashes, key by key; None if the upload is not a
    complete bundled set from a single replayable scenario."""
    known = known_specimen_hashes()
    candidates: set[str] | None = None
    for key in DOCUMENT_KEYS:
        digest = provenance.get(key)
        matches = {name for (name, k) in known.get(digest, set()) if k == key}
        candidates = matches if candidates is None else candidates & matches
        if not candidates:
            return None
    for name in sorted(candidates or ()):
        if SCENARIOS[name].has_recording():
            return name
    return None


def load_recording(scenario: Scenario) -> dict[str, dict]:
    data = json.loads(scenario.recording_path.read_text())
    data.pop("note", None)
    return data


def recorded_responses_by_hash() -> dict[str, dict]:
    """sha256 of a specimen's bytes -> the recorded Converse JSON for it,
    for every scenario that has both its specimens and a recording."""
    by_hash: dict[str, dict] = {}
    for scenario in SCENARIOS.values():
        if not (scenario.has_specimens() and scenario.has_recording()):
            continue
        recording = load_recording(scenario)
        for key in DOCUMENT_KEYS:
            if key in recording:
                by_hash[sha256_bytes(scenario.specimen_path(key).read_bytes())] = recording[key]
    return by_hash


def scenario_summaries() -> list[dict]:
    return [
        {
            "name": s.name,
            "title": s.title,
            "description": s.description,
            "expected": s.expected,
            "available_offline": s.has_specimens() and s.has_recording(),
        }
        for s in SCENARIOS.values()
        if s.has_specimens()
    ]
