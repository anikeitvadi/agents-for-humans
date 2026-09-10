"""Attorney-review draft composition.

The safety-critical boundary text (the rule's deterministic message, always
framed as a flag for attorney review, never a legal conclusion) is a fixed
core that is always present in the output verbatim. A Strands `Agent`, when
supplied, may only prepend a short personalized intro around that core — it
can never replace or edit the core, and any Agent failure falls back to the
deterministic core alone rather than blocking the draft.

This is the one place in the immigration pack that genuinely invokes the
Strands Agents SDK rather than a raw Bedrock call — see
docs/architecture-spec.md §4.2 for why extraction stays on the raw Bedrock
Converse API (multimodal document blocks) while drafting (plain text in,
text out) goes through `strands.Agent`.
"""

from dataclasses import dataclass

import boto3
from strands import Agent

_INTRO_PROMPT = (
    "Write a brief, plain, one-paragraph email intro to an immigration attorney "
    "about the case below named '{case_name}'. Do not state any legal conclusion, "
    "eligibility determination, or advice — only that something needs their review."
)

_CLOSING = (
    "\n\nPlease advise on next steps. This message was generated automatically "
    "and is not legal advice."
)


@dataclass
class DraftResult:
    subject: str
    body: str
    used_llm_personalization: bool


def build_attorney_draft(rule_message: str, subject_facts: dict, agent: Agent | None = None) -> DraftResult:
    case_name = subject_facts.get("case_name", "immigration documents")
    subject = f"Document review needed: {case_name}"
    core = f"An automated check flagged the following for your review:\n\n{rule_message}" + _CLOSING

    if agent is None:
        return DraftResult(subject=subject, body=core, used_llm_personalization=False)

    try:
        result = agent(_INTRO_PROMPT.format(case_name=case_name))
        intro = str(result)
    except Exception:
        return DraftResult(subject=subject, body=core, used_llm_personalization=False)

    body = f"{intro}\n\n{core}"
    return DraftResult(subject=subject, body=body, used_llm_personalization=True)


def _has_aws_credentials() -> bool:
    return boto3.Session().get_credentials() is not None


def build_bedrock_agent(model_id: str) -> Agent | None:
    """Build a real Strands Agent backed by Bedrock, or None if no AWS
    credentials are configured. Checking credentials up front (rather than
    letting agent() fail at call time) keeps local/CI runs fast and
    deterministic instead of hanging on network/credential-provider
    lookups — the deterministic core in build_attorney_draft is a fully
    correct fallback either way.
    """
    if not _has_aws_credentials():
        return None

    from strands.models import BedrockModel

    return Agent(
        model=BedrockModel(model_id=model_id),
        system_prompt="You write brief, plain, one-paragraph email intros for an immigration attorney. "
        "Never state a legal conclusion, eligibility determination, or advice.",
    )
