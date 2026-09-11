import json

import botocore.session
from botocore.validate import validate_parameters

from agent.llm.extract import extract_fields

_CONVERSE_OPERATION = (
    botocore.session.get_session().get_service_model("bedrock-runtime").operation_model("Converse")
)


class _FakeBedrockClient:
    """Stands in for boto3's bedrock-runtime client. Real Bedrock calls
    require AWS credentials/model access that aren't available in this
    session (Day-1 human prerequisite) — the extraction *logic* (evidence,
    missing/ambiguous handling, needs_review) is what must be proven here,
    independent of the live API.

    Records the kwargs it was called with so tests can validate the request
    shape against botocore's real Converse operation schema — a fake that
    merely accepts arbitrary kwargs would hide a missing required parameter.
    """

    def __init__(self, response_text: str):
        self._response_text = response_text
        self.last_request: dict | None = None

    def converse(self, **kwargs):
        validate_parameters(kwargs, _CONVERSE_OPERATION.input_shape)
        self.last_request = kwargs
        return {"output": {"message": {"content": [{"text": self._response_text}]}}}


def _canned_response(fields: dict) -> str:
    return json.dumps(fields)


def test_all_fields_extracted_cleanly_needs_no_review():
    client = _FakeBedrockClient(
        _canned_response(
            {
                "admit_until": {"value": "2026-11-03", "evidence": "Admit Until Date: 11/03/2026", "status": "extracted"},
            }
        )
    )

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is False
    assert result.fields["admit_until"].value == "2026-11-03"
    assert result.fields["admit_until"].evidence == "Admit Until Date: 11/03/2026"
    assert client.last_request["modelId"] == "fake-model-id"


def test_missing_field_triggers_needs_review():
    client = _FakeBedrockClient(
        _canned_response(
            {
                "admit_until": {"value": None, "evidence": "", "status": "missing"},
            }
        )
    )

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True
    assert result.fields["admit_until"].status == "missing"


def test_ambiguous_field_triggers_needs_review():
    client = _FakeBedrockClient(
        _canned_response(
            {
                "admit_until": {
                    "value": "2026-11-03 or 2026-12-03 (unclear scan)",
                    "evidence": "smudged stamp",
                    "status": "ambiguous",
                },
            }
        )
    )

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True
    assert result.fields["admit_until"].status == "ambiguous"


def test_malformed_model_response_is_treated_as_needs_review_not_a_crash():
    client = _FakeBedrockClient("not valid json at all")

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True
    assert result.error is not None


def test_null_value_with_status_extracted_is_not_trusted():
    # A model can claim "extracted" while providing no actual value — that
    # must not pass as a clean, review-free extraction.
    client = _FakeBedrockClient(
        _canned_response({"admit_until": {"value": None, "evidence": "", "status": "extracted"}})
    )

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True


def test_empty_evidence_with_status_extracted_is_not_trusted():
    client = _FakeBedrockClient(
        _canned_response({"admit_until": {"value": "2026-11-03", "evidence": "", "status": "extracted"}})
    )

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True


def test_unsupported_status_value_routes_to_review():
    client = _FakeBedrockClient(
        _canned_response({"admit_until": {"value": "2026-11-03", "evidence": "stamp", "status": "confident"}})
    )

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True


def test_non_object_json_response_is_needs_review_not_a_crash():
    client = _FakeBedrockClient(json.dumps(["admit_until", "not", "an", "object"]))

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True
    assert result.error is not None


def test_null_field_entry_is_treated_as_missing_not_a_crash():
    client = _FakeBedrockClient(_canned_response({"admit_until": None}))

    result = extract_fields(client, document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id")

    assert result.needs_review is True
    assert result.fields["admit_until"].status == "missing"


def test_missing_content_in_response_envelope_is_needs_review_not_a_crash():
    class _EmptyContentClient:
        def converse(self, **kwargs):
            return {"output": {"message": {"content": []}}}

    result = extract_fields(
        _EmptyContentClient(), document_bytes=b"pdf-bytes", document_format="pdf", field_names=["admit_until"], model_id="fake-model-id"
    )

    assert result.needs_review is True
    assert result.error is not None
