"""Chooses between a live Bedrock client and a recorded-response client for
document extraction, so the same extract_fields() validation logic
(agent/llm/extract.py) runs either way — only the source of the raw
Converse response text changes. Mirrors the has-credentials pattern in
agent/llm/draft.py::build_bedrock_agent.

Callers must surface the returned mode ("live" or "recorded") wherever the
extraction result is shown — a recorded replay must never be presented as a
live parse (see docs/implementation-handoff-2026-09-10.md C1).
"""

import json
import re
from pathlib import Path
from typing import Literal

import boto3

_REFERENCE_ID_PATTERN = re.compile(r"reference id: '([^']*)'")

RECORDED_RESPONSES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_case" / "recorded_extraction_response.json"
)

ExtractionMode = Literal["live", "recorded"]


def has_aws_credentials() -> bool:
    return boto3.Session().get_credentials() is not None


def build_live_bedrock_client(region_name: str = "us-east-1"):
    return boto3.client("bedrock-runtime", region_name=region_name)


class RecordedResponseClient:
    """Fake Converse client that replays a canned response per document
    name. Used when no live AWS credentials are configured, so the
    demo/offline paths stay deterministic without a network call.
    """

    def __init__(self, responses: dict[str, dict] | None = None):
        self._responses = responses if responses is not None else self._load_default()

    @staticmethod
    def _load_default() -> dict[str, dict]:
        data = json.loads(RECORDED_RESPONSES_PATH.read_text())
        data.pop("note", None)
        return data

    def converse(self, **kwargs):
        document_name = _document_name_from_request(kwargs)
        if document_name not in self._responses:
            raise KeyError(f"no recorded response for document '{document_name}'")
        return {"output": {"message": {"content": [{"text": json.dumps(self._responses[document_name])}]}}}


def _document_name_from_request(kwargs: dict) -> str:
    # Image blocks (PNG/JPEG/etc — R1) carry no `name` field, so the
    # document's reference id is embedded in the prompt text instead; this
    # is a recorded-client identification concern only, not part of the
    # real AWS request contract.
    for message in kwargs.get("messages", []):
        for block in message.get("content", []):
            text = block.get("text")
            if text:
                match = _REFERENCE_ID_PATTERN.search(text)
                if match:
                    return match.group(1)
    raise ValueError("Converse request did not include a document reference id")


def _describe_failure(exc: Exception) -> str:
    """Short, human-readable cause: botocore's own message when present
    (e.g. "ValidationException: Error 002: ..."), else the exception."""
    response = getattr(exc, "response", None)
    if isinstance(response, dict) and isinstance(response.get("Error"), dict):
        error = response["Error"]
        return f"{error.get('Code', type(exc).__name__)}: {error.get('Message', '')}"[:200]
    return f"{type(exc).__name__}: {str(exc)[:160]}"


class FailoverExtractionClient:
    """Tries live Bedrock first and falls back to the recorded replay on the
    first API failure (denied account, no model access, network), then stays
    on the replay for the life of the process. Credentials being present is
    not proof that Bedrock works, so the truthful mode is only known after a
    call: read `mode` and `fallback_reason` after extraction, never before.

    A batch that fails over part-way is labeled "recorded", never "live":
    the label errs toward the less impressive claim. Callers that make
    multiple calls per case (agent/packs/immigration/pipeline.py) must
    additionally check whether `mode` *changed* between calls — a client
    that starts live and fails over mid-batch has already mixed a genuine
    live result with recorded ones, which no single final label can fix.
    """

    def __init__(self, live_client=None, recorded_client: RecordedResponseClient | None = None):
        self._live = live_client
        self._recorded = recorded_client if recorded_client is not None else RecordedResponseClient()
        self.mode: ExtractionMode = "live" if live_client is not None else "recorded"
        self.fallback_reason: str | None = None if live_client is not None else "no AWS credentials configured"

    def converse(self, **kwargs):
        if self._live is not None and self.mode == "live":
            try:
                return self._live.converse(**kwargs)
            except Exception as exc:  # noqa: BLE001 - any live failure must degrade, never crash the demo
                self.mode = "recorded"
                self.fallback_reason = f"live Bedrock extraction unavailable ({_describe_failure(exc)}); replaying the recorded response"
        return self._recorded.converse(**kwargs)


def build_extraction_client(region_name: str = "us-east-1") -> tuple[FailoverExtractionClient, ExtractionMode]:
    """Returns the failover client and its *initial* mode. The mode after a
    call is on the client itself (`client.mode`)."""
    live = build_live_bedrock_client(region_name=region_name) if has_aws_credentials() else None
    client = FailoverExtractionClient(live)
    return client, client.mode
