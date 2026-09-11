"""Keep the offline suite hermetic on machines that have AWS credentials.

Every code path that touches Bedrock chooses live mode when boto3 can find
credentials (agent/llm/document_client.py, agent/llm/draft.py). Without this
fixture, a developer with ~/.aws configured would see the offline tests make
real Bedrock calls. Tests marked `live` opt back in.
"""

import pytest


@pytest.fixture(autouse=True)
def _hide_aws_credentials(request, monkeypatch, tmp_path_factory):
    if request.node.get_closest_marker("live"):
        return
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    empty = tmp_path_factory.mktemp("no-aws")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(empty / "credentials"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(empty / "config"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
