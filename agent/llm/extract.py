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
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

FieldStatus = Literal["extracted", "missing", "ambiguous"]
_ALLOWED_STATUSES = {"extracted", "missing", "ambiguous"}

# AWS Bedrock's ImageBlock format enum — these formats must be sent as an
# ImageBlock, never a DocumentBlock (R1: DocumentBlock's format enum
# excludes them). "jpg" is normalized to the enum's "jpeg".
_IMAGE_FORMATS = {"png": "png", "jpeg": "jpeg", "jpg": "jpeg", "gif": "gif", "webp": "webp"}

_EXTRACTION_PROMPT = (
    "Extract the following fields from the attached document (reference id: "
    "'{document_name}'). For each field, "
    "respond with a JSON object keyed by field name, where each value is an "
    "object with: 'value' (the extracted value, or null if not found), "
    "'evidence' (the exact source text you based the value on), and 'status' "
    "(one of 'extracted', 'missing', 'ambiguous'). Use 'ambiguous' if the "
    "document contains conflicting or illegible information for a field. "
    "Do not guess a value you cannot support with evidence from the document. "
    "{date_instruction}"
    "Respond with only the raw JSON object — no markdown code fences, no "
    "commentary before or after it. "
    "Fields to extract: {fields}"
)

_DATE_INSTRUCTION = (
    "For any of these fields that is a date ({date_fields}), report 'value' "
    "normalized to ISO 8601 (YYYY-MM-DD) regardless of the format printed on "
    "the document, while 'evidence' must still be the exact original printed "
    "text you based it on (do not normalize the evidence). "
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
    date_fields: list[str] | None = None,
) -> ExtractionResult:
    date_instruction = _DATE_INSTRUCTION.format(date_fields=", ".join(date_fields)) if date_fields else ""
    prompt = _EXTRACTION_PROMPT.format(fields=", ".join(field_names), document_name=document_name, date_instruction=date_instruction)
    image_format = _IMAGE_FORMATS.get(document_format.lower())
    if image_format is not None:
        media_block = {"image": {"format": image_format, "source": {"bytes": document_bytes}}}
    else:
        media_block = {"document": {"format": document_format, "name": document_name, "source": {"bytes": document_bytes}}}

    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}, media_block]}],
        )
    except Exception as exc:  # network/model failures must not crash the pipeline (R3)
        return ExtractionResult(fields={}, needs_review=True, error=f"extraction request failed: {exc}")

    try:
        raw_text = response["output"]["message"]["content"][0]["text"]
        parsed = json.loads(_strip_code_fence(raw_text))
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        return ExtractionResult(fields={}, needs_review=True, error=f"could not parse model response: {exc}")

    if not isinstance(parsed, dict):
        return ExtractionResult(fields={}, needs_review=True, error="model response was not a JSON object")

    date_field_set = set(date_fields) if date_fields else set()
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

        # status must be hashable and a member of the allowed set — a list/
        # dict status would raise TypeError on the `in` check below (R3).
        if not isinstance(status, str) or status not in _ALLOWED_STATUSES:
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

        # A field value must be a plain string, never a list/object — those
        # cannot be trusted as a single extracted value (R3).
        if status == "extracted" and not isinstance(value, str):
            fields[name] = FieldResult(value=value, evidence=evidence, status="ambiguous")
            needs_review = True
            continue

        # A date field's value must actually parse as an ISO date before it
        # can feed date arithmetic downstream — a plausible printed value
        # like "11/03/2026" or an impossible date must route to review
        # instead of crashing the rule engine later (R3).
        if status == "extracted" and name in date_field_set and not _is_iso_date(value):
            fields[name] = FieldResult(value=value, evidence=evidence, status="ambiguous")
            needs_review = True
            continue

        fields[name] = FieldResult(value=value, evidence=evidence, status=status)
        if status != "extracted":
            needs_review = True

    return ExtractionResult(fields=fields, needs_review=needs_review, error=None)


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


_CODE_FENCE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """A real model reliably wraps JSON responses in a markdown code fence
    even when asked not to; the prompt instruction alone is not sufficient
    (confirmed against live Bedrock — recorded/fixture responses never had
    this, so it stayed hidden until live verification). Strip a single
    leading/trailing fence if present; otherwise return the text unchanged
    so json.loads still reports a clear error on genuinely malformed output."""
    match = _CODE_FENCE.match(text.strip())
    return match.group(1) if match else text
