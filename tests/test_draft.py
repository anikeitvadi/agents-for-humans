from strands import Agent
from strands.models import Model

from agent.llm.draft import build_attorney_draft

RULE_MESSAGE = (
    "Your I-94 admit-until date and I-797 validity end date disagree by 55 day(s) "
    "(I-94 is earlier). These documents disagree — this is a flag to review with "
    "your attorney, not a status determination."
)


class _FakeModel(Model):
    """Minimal strands.models.Model conformer for offline testing — no live
    Bedrock call. Modeled on strands-agents/harness-sdk's own
    tests/fixtures/mocked_model_provider.py test-double pattern.
    """

    def __init__(self, text=None, raises=False):
        self._text = text
        self._raises = raises

    def update_config(self, **kwargs):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        return
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        if self._raises:
            raise RuntimeError("simulated Bedrock outage")
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": self._text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}


def _agent_with(text=None, raises=False):
    return Agent(model=_FakeModel(text=text, raises=raises), system_prompt="You draft brief attorney-review email intros.")


def test_without_agent_uses_deterministic_core_only():
    draft = build_attorney_draft(rule_message=RULE_MESSAGE, subject_facts={"case_name": "Sample Case"})

    assert RULE_MESSAGE in draft.body
    assert draft.used_llm_personalization is False
    assert "not legal advice" in draft.body.lower()


def test_with_working_agent_prepends_personalized_intro():
    agent = _agent_with(text="Hi there — flagging something for your review.")

    draft = build_attorney_draft(rule_message=RULE_MESSAGE, subject_facts={"case_name": "Sample Case"}, agent=agent)

    assert draft.used_llm_personalization is True
    assert "Hi there" in draft.body
    # The deterministic safety-critical core must still be present verbatim.
    assert RULE_MESSAGE in draft.body


def test_agent_failure_falls_back_to_deterministic_core_without_crashing():
    agent = _agent_with(raises=True)

    draft = build_attorney_draft(rule_message=RULE_MESSAGE, subject_facts={"case_name": "Sample Case"}, agent=agent)

    assert draft.used_llm_personalization is False
    assert RULE_MESSAGE in draft.body


def test_draft_never_states_a_legal_conclusion():
    draft = build_attorney_draft(rule_message=RULE_MESSAGE, subject_facts={"case_name": "Sample Case"})

    for forbidden in ("unlawful presence", "you are not in status", "you must leave", "file the i-485"):
        assert forbidden not in draft.body.lower()
