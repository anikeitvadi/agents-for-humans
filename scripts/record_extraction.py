"""Record live Bedrock extraction responses for a bundled scenario, so the
demo can replay them offline with the truthful "recorded" label.

Run on a machine whose AWS account has Bedrock model access:

    .venv/bin/python scripts/record_extraction.py --scenario matching
    .venv/bin/python scripts/record_extraction.py --all

Writes fixtures/sample_case/scenarios/<name>/recorded_extraction_response.json
in the same format as fixtures/sample_case/recorded_extraction_response.json:
the raw JSON object the model returned per document, keyed by document key.
The recorder wraps the real client and captures exactly what the pipeline
saw, through the same prompt and validation path the app uses.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import BEDROCK_MODEL_ID  # noqa: E402
from agent.llm.document_client import _document_name_from_request, build_live_bedrock_client, has_aws_credentials  # noqa: E402
from agent.llm.extract import _strip_code_fence  # noqa: E402
from agent.packs.immigration.pipeline import extract_case_documents  # noqa: E402
from agent.packs.immigration.scenarios import DOCUMENT_KEYS, SCENARIOS, get_scenario  # noqa: E402


class RecordingClient:
    """Passes every Converse call to the live client and keeps the raw
    response text, keyed by the document reference id in the prompt."""

    def __init__(self, live):
        self._live = live
        self.raw: dict[str, str] = {}

    def converse(self, **kwargs):
        response = self._live.converse(**kwargs)
        self.raw[_document_name_from_request(kwargs)] = response["output"]["message"]["content"][0]["text"]
        return response


def record(scenario_name: str) -> Path:
    scenario = get_scenario(scenario_name)
    if not scenario.has_specimens():
        raise SystemExit(f"scenario '{scenario_name}' has no specimens; run fixtures/sample_case/generate_specimens.py first")
    client = RecordingClient(build_live_bedrock_client())
    documents = {key: scenario.specimen_path(key).read_bytes() for key in DOCUMENT_KEYS}
    extraction = extract_case_documents(client, mode="live", model_id=BEDROCK_MODEL_ID, documents=documents)
    if extraction.mode != "live" or any(key not in client.raw for key in DOCUMENT_KEYS):
        raise SystemExit(f"live extraction did not complete: mode={extraction.mode} reason={extraction.mode_reason}")
    recording = {
        "note": (
            f"Recorded live Bedrock Converse response text for the '{scenario.name}' scenario "
            f"({scenario.title}), captured by scripts/record_extraction.py against model {BEDROCK_MODEL_ID}. "
            "Replayed offline by agent/llm/document_client.py::RecordedResponseClient, matched by the sha256 of "
            "each specimen's bytes. Not a source of truth independent of live extraction."
        )
    }
    for key in DOCUMENT_KEYS:
        recording[key] = json.loads(_strip_code_fence(client.raw[key]))
    scenario.recording_path.parent.mkdir(parents=True, exist_ok=True)
    scenario.recording_path.write_text(json.dumps(recording, indent=2) + "\n")
    print(f"{scenario.name}: fields={extraction.fields} needs_review={extraction.needs_review} -> {scenario.recording_path}")
    return scenario.recording_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), help="one scenario to record")
    parser.add_argument("--all", action="store_true", help="record every scenario (overwrites existing recordings)")
    args = parser.parse_args()
    if not (args.scenario or args.all):
        parser.error("choose --scenario NAME or --all")
    if not has_aws_credentials():
        raise SystemExit("no AWS credentials configured; this script needs live Bedrock access")
    names = sorted(SCENARIOS) if args.all else [args.scenario]
    for name in names:
        record(name)


if __name__ == "__main__":
    main()
