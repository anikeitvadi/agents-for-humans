"""Document field extraction via Bedrock's Converse API.

Structured output validates *structure*, not *facts* — a plausible but
wrong date passes any schema and produces a confidently wrong downstream
answer. So every extracted field carries per-field evidence (the source
text the model based it on) and an explicit status (extracted / missing /
ambiguous). A missing or ambiguous critical field routes to needs_review
instead of a false-confident value. The rules engine (agent/packs/*/rules.py)
must never receive a value without knowing whether it was actually read
off the document or guessed.

The bedrock client is injected so this logic is unit-testable without a
live AWS call — see tests/test_extraction.py for the fake-client contract.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Literal

FieldStatus = Literal["extracted", "missing", "ambiguous"]
_ALLOWED_STATUSES = {"extracted", "missing", "ambiguous"}

_EXTRACTION_PROMPT = (
    "Extract the following fields from the attached document. For each field, "
    "respond with a JSON object keyed by field name, where each value is an "
    "object with: 'value' (the extracted value, or null if not found), "
    "'evidence' (the exact source text you based the value on), and 'status' "
    "(one of 'extracted', 'missing', 'ambiguous'). Use 'ambiguous' if the "
    "document contains conflicting or illegible information for a field. "
    "Do not guess a value you cannot support with evidence from the document. "
    "Fields to extract: {fields}"
)


@dataclass
class FieldResult:
    value: Any
    evidence: str
    status: FieldStatus


@dataclass
class ExtractionResult:
    fields: dict[str, FieldResult] = field(default_factory=dict)
    needs_review: bool = False
    error: str | None = None


def extract_fields(
    bedrock_client,
    document_bytes: bytes,
    document_format: str,
    field_names: list[str],
    model_id: str,
    document_name: str = "document",
) -> ExtractionResult:
    prompt = _EXTRACTION_PROMPT.format(fields=", ".join(field_names))
    response = bedrock_client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {"text": prompt},
                    {
                        "document": {
                            "format": document_format,
                            "name": document_name,
                            "source": {"bytes": document_bytes},
                        }
                    },
                ],
            }
        ],
    )

    try:
        raw_text = response["output"]["message"]["content"][0]["text"]
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        return ExtractionResult(fields={}, needs_review=True, error=f"could not parse model response: {exc}")

    if not isinstance(parsed, dict):
        return ExtractionResult(fields={}, needs_review=True, error="model response was not a JSON object")

    fields: dict[str, FieldResult] = {}
    needs_review = False
    for name in field_names:
        raw = parsed.get(name)
        if not isinstance(raw, dict):
            fields[name] = FieldResult(value=None, evidence="", status="missing")
            needs_review = True
            continue

        status = raw.get("status")
        value = raw.get("value")
        evidence = raw.get("evidence")
        evidence = evidence if isinstance(evidence, str) else ""

        if status not in _ALLOWED_STATUSES:
            # An unsupported status is not evidence the model actually read
            # the field — don't pass through a value we can't trust either.
            fields[name] = FieldResult(value=None, evidence=evidence, status="ambiguous")
            needs_review = True
            continue

        # A model claiming "extracted" without a real value or supporting
        # evidence is a contract violation, not a clean read — F4.
        extracted_but_empty = status == "extracted" and (
            value is None or (isinstance(value, str) and not value.strip()) or not evidence.strip()
        )
        if extracted_but_empty:
            fields[name] = FieldResult(value=value, evidence=evidence, status="ambiguous")
            needs_review = True
            continue

        fields[name] = FieldResult(value=value, evidence=evidence, status=status)
        if status != "extracted":
            needs_review = True

    return ExtractionResult(fields=fields, needs_review=needs_review, error=None)
