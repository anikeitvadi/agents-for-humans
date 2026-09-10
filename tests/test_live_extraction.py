"""Live Bedrock extraction check against the real specimen images —
excluded from the default `pytest -q` run (see pyproject.toml's `-m "not
live"` addopts) so the offline suite never needs AWS credentials or a
network call. Run explicitly with:

    .venv/bin/python -m pytest -m live tests/test_live_extraction.py

This proves the extraction *contract* (agent/llm/extract.py) against real
Bedrock output for the same specimen bytes the recorded-response fixture
claims to represent — the recorded fixture is not itself proof that live
extraction works (docs/implementation-handoff-2026-09-10.md C1).
"""

import pytest

from agent.config import BEDROCK_MODEL_ID
from agent.llm.document_client import build_live_bedrock_client, has_aws_credentials
from agent.llm.extract import extract_fields
from agent.packs.immigration.pipeline import SPECIMENS_DIR

pytestmark = pytest.mark.live


def _require_aws_credentials():
    if not has_aws_credentials():
        pytest.skip("no AWS credentials configured in this environment")


def test_live_extraction_reads_admit_until_from_i94_specimen():
    _require_aws_credentials()
    client = build_live_bedrock_client()

    result = extract_fields(
        client,
        document_bytes=(SPECIMENS_DIR / "i94.png").read_bytes(),
        document_format="png",
        field_names=["admit_until"],
        model_id=BEDROCK_MODEL_ID,
        document_name="i94",
    )

    assert result.needs_review is False
    assert result.fields["admit_until"].value == "2026-11-03"


def test_live_extraction_reads_i797_valid_until_from_i797_specimen():
    _require_aws_credentials()
    client = build_live_bedrock_client()

    result = extract_fields(
        client,
        document_bytes=(SPECIMENS_DIR / "i797.png").read_bytes(),
        document_format="png",
        field_names=["i797_valid_until"],
        model_id=BEDROCK_MODEL_ID,
        document_name="i797",
    )

    assert result.needs_review is False
    assert result.fields["i797_valid_until"].value == "2026-12-28"


def test_live_extraction_reads_passport_expiry_from_passport_specimen():
    _require_aws_credentials()
    client = build_live_bedrock_client()

    result = extract_fields(
        client,
        document_bytes=(SPECIMENS_DIR / "passport.png").read_bytes(),
        document_format="png",
        field_names=["passport_expiry"],
        model_id=BEDROCK_MODEL_ID,
        document_name="passport",
    )

    assert result.needs_review is False
    assert result.fields["passport_expiry"].value == "2026-11-03"
