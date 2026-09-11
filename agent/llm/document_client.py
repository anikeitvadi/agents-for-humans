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
from pathlib import Path
from typing import Literal

import boto3

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
    for message in kwargs.get("messages", []):
        for block in message.get("content", []):
            if "document" in block:
                return block["document"]["name"]
    raise ValueError("Converse request did not include a document block")


def build_extraction_client(region_name: str = "us-east-1") -> tuple[object, ExtractionMode]:
    if has_aws_credentials():
        return build_live_bedrock_client(region_name=region_name), "live"
    return RecordedResponseClient(), "recorded"
