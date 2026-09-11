from unittest.mock import patch

import pytest

from agent.llm.document_client import FailoverExtractionClient, RecordedResponseClient, build_extraction_client
from agent.llm.extract import extract_fields


def _i94_request_kwargs(document_name="i94"):
    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"text": f"extract admit_until (reference id: '{document_name}')"},
                    {"image": {"format": "png", "source": {"bytes": b"fake"}}},
                ],
            }
        ]
    }


def test_recorded_response_client_replays_canned_response_for_known_document():
    client = RecordedResponseClient()

    response = client.converse(**_i94_request_kwargs("i94"))

    text = response["output"]["message"]["content"][0]["text"]
    assert "2026-11-03" in text


def test_recorded_response_client_raises_for_unknown_document():
    client = RecordedResponseClient()

    with pytest.raises(KeyError):
        client.converse(**_i94_request_kwargs("not-a-real-document"))


def test_recorded_response_client_raises_when_request_has_no_reference_id():
    client = RecordedResponseClient()

    with pytest.raises(ValueError):
        client.converse(messages=[{"role": "user", "content": [{"text": "no reference id here"}]}])


def test_extract_fields_parses_i94_specimen_response_via_recorded_client():
    client = RecordedResponseClient()

    result = extract_fields(
        client,
        document_bytes=b"fake",
        document_format="png",
        field_names=["admit_until"],
        model_id="fake-model-id",
        document_name="i94",
    )

    assert result.needs_review is False
    assert result.fields["admit_until"].value == "2026-11-03"
    assert result.fields["admit_until"].evidence == "Admit Until Date: 11/03/2026"


def test_extract_fields_parses_i797_specimen_response_via_recorded_client():
    client = RecordedResponseClient()

    result = extract_fields(
        client,
        document_bytes=b"fake",
        document_format="png",
        field_names=["i797_valid_until"],
        model_id="fake-model-id",
        document_name="i797",
    )

    assert result.needs_review is False
    assert result.fields["i797_valid_until"].value == "2026-12-28"


def test_extract_fields_parses_passport_specimen_response_via_recorded_client():
    client = RecordedResponseClient()

    result = extract_fields(
        client,
        document_bytes=b"fake",
        document_format="png",
        field_names=["passport_expiry"],
        model_id="fake-model-id",
        document_name="passport",
    )

    assert result.needs_review is False
    assert result.fields["passport_expiry"].value == "2026-11-03"


def test_build_extraction_client_uses_recorded_mode_without_aws_credentials():
    with patch("agent.llm.document_client.has_aws_credentials", return_value=False):
        client, mode = build_extraction_client()

    assert mode == "recorded"
    assert isinstance(client, FailoverExtractionClient)
    assert client.mode == "recorded"
    assert "no AWS credentials" in client.fallback_reason


def test_build_extraction_client_uses_live_mode_with_aws_credentials():
    with patch("agent.llm.document_client.has_aws_credentials", return_value=True), patch(
        "agent.llm.document_client.build_live_bedrock_client", return_value="fake-boto3-client"
    ):
        client, mode = build_extraction_client()

    # Credentials are only the *intent* to go live; the failover client
    # proves it per call and downgrades the label on the first failure.
    assert mode == "live"
    assert isinstance(client, FailoverExtractionClient)
    assert client.mode == "live"
    assert client.fallback_reason is None
