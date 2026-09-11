from strands import Agent

import agent.llm.draft as draft_module
from agent.llm.draft import build_bedrock_agent


def test_returns_none_without_aws_credentials(monkeypatch):
    monkeypatch.setattr(draft_module, "_has_aws_credentials", lambda: False)

    assert build_bedrock_agent(model_id="fake-model-id") is None


def test_returns_an_agent_when_credentials_are_present(monkeypatch):
    monkeypatch.setattr(draft_module, "_has_aws_credentials", lambda: True)

    result = build_bedrock_agent(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")

    assert isinstance(result, Agent)
