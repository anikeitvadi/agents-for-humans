"""The guardian agent: Strands tools over the engine, driven offline by a
scripted model so the real tool registration and loop are exercised."""

import json
from pathlib import Path

import pytest

from agent.config import BEDROCK_MODEL_ID
from agent.engine.store import Store
from agent.llm.document_client import RecordedResponseClient
from agent.llm.guardian import SYSTEM_PROMPT, ask_guardian, build_guardian_tools, tool_names
from agent.packs.immigration.bulletin import PRIOR_CAPTURED_MONTH
from agent.packs.recalls.feed import load_fallback_recall
from tests.scripted_model import ScriptedModel

RECEIPTS = Path(__file__).resolve().parent.parent / "fixtures" / "recalls" / "receipts.json"
EXPECTED_TOOLS = ["check_document_dates", "run_sample_case_check", "check_uploaded_case", "check_visa_bulletin", "check_recall"]


def _receipts() -> dict:
    return json.loads(RECEIPTS.read_text())


@pytest.fixture
def tools(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    return build_guardian_tools(
        store,
        extraction_client=RecordedResponseClient(),
        extraction_mode="recorded",
        model_id=BEDROCK_MODEL_ID,
        recall_item=load_fallback_recall(),
        recall_mode="fallback",
        receipts_loader=_receipts,
        prior_bulletin_months=PRIOR_CAPTURED_MONTH,
    )


def test_tool_names_and_schemas(tools):
    assert tool_names(tools) == EXPECTED_TOOLS
    dates_spec = tools[0].tool_spec
    assert set(dates_spec["inputSchema"]["json"]["required"]) == {"i94_admit_until", "i797_valid_until"}
    assert "never a status" in dates_spec["description"]


def test_tools_work_as_plain_functions(tools):
    dates, sample, uploaded, bulletin, recall = tools

    gap = dates(i94_admit_until="2026-11-03", i797_valid_until="2026-12-28")
    assert gap["status"] == "success"
    assert gap["content"][0]["json"]["gap_days"] == 55
    assert dates(i94_admit_until="not-a-date", i797_valid_until="2026-12-28")["status"] == "error"

    case = sample()["content"][0]["json"]
    assert case["extraction_mode"] == "recorded"
    assert case["decision"] == "surfaced"
    assert "55" in case["draft"]["body"]

    assert uploaded()["status"] == "error"  # no submission ref bound in this fixture

    october = bulletin(month="2025-10")["content"][0]["json"]
    assert october["cutoff_status"] == "current"
    assert october["decision"] == "surfaced"
    assert bulletin(month="1999-01")["status"] == "error"

    matched = recall(receipt="seeded")["content"][0]["json"]
    assert matched["matched"] is True
    assert matched["decision"] == "surfaced"
    assert recall(receipt="unmatched")["content"][0]["json"]["matched"] is False


def test_check_uploaded_case_reports_the_bound_submission(tmp_path):
    from agent.packs.immigration.pipeline import run_case_from_documents, SPECIMENS_DIR

    store = Store(str(tmp_path / "ledger.db"))
    documents = {key: (SPECIMENS_DIR / f"{key}.png").read_bytes() for key in ("i94", "i797", "passport")}
    processed = run_case_from_documents(
        store, clock_id="c1", client=RecordedResponseClient(), mode="recorded", model_id=BEDROCK_MODEL_ID, documents=documents
    )

    bound_tools = build_guardian_tools(
        store,
        extraction_client=RecordedResponseClient(),
        extraction_mode="recorded",
        model_id=BEDROCK_MODEL_ID,
        recall_item=load_fallback_recall(),
        recall_mode="fallback",
        receipts_loader=_receipts,
        prior_bulletin_months=PRIOR_CAPTURED_MONTH,
        current_submission_ref=processed.ref,
    )
    _, _, check_uploaded_case, _, _ = bound_tools

    result = check_uploaded_case()["content"][0]["json"]
    assert result["decision"] == "surfaced"
    assert result["fields"]["admit_until"] == "2026-11-03"
    assert result["draft"] is not None


def test_check_uploaded_case_with_a_cleared_ref_reports_not_found(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    bound_tools = build_guardian_tools(
        store,
        extraction_client=RecordedResponseClient(),
        extraction_mode="recorded",
        model_id=BEDROCK_MODEL_ID,
        recall_item=load_fallback_recall(),
        recall_mode="fallback",
        receipts_loader=_receipts,
        prior_bulletin_months=PRIOR_CAPTURED_MONTH,
        current_submission_ref={"clock_id": "c1", "event_id": "doc-nonexistent", "rule_version": "v1"},
    )
    _, _, check_uploaded_case, _, _ = bound_tools

    assert check_uploaded_case()["status"] == "error"


def test_agent_calls_the_date_tool_and_reports_it(tools):
    model = ScriptedModel(
        [
            ("tool", "check_document_dates", {"i94_admit_until": "2026-11-03", "i797_valid_until": "2026-12-28"}),
            ("text", "Your two documents disagree by 55 days. This is a flag for your attorney, not a status determination."),
        ]
    )

    result = ask_guardian(model, tools, "Do my documents disagree?")

    assert result.error is None
    assert result.tools_called == ["check_document_dates"]
    assert "55 days" in result.answer
    # Strands registered every tool and our system prompt on the real model call.
    assert model.calls[0]["tools"] == EXPECTED_TOOLS
    assert model.calls[0]["system_prompt"] == SYSTEM_PROMPT
    # The real tool ran and its result was fed back to the model.
    fed = model.last_tool_result()
    assert fed["status"] == "success"
    assert fed["content"][0]["json"]["gap_days"] == 55


def test_agent_runs_the_sample_case_through_the_shared_engine(tools):
    model = ScriptedModel([("tool", "run_sample_case_check", {}), ("text", "One thing needs your review; a draft is ready.")])

    first = ask_guardian(model, tools, "Check the sample case.")
    assert first.tools_called == ["run_sample_case_check"]
    assert model.last_tool_result()["content"][0]["json"]["decision"] == "surfaced"

    # Same engine, same ledger: asking again is silent, not a second ping.
    model = ScriptedModel([("tool", "run_sample_case_check", {}), ("text", "Nothing new.")])
    ask_guardian(model, tools, "Check it again.")
    again = model.last_tool_result()["content"][0]["json"]
    assert again["decision"] == "silent"
    assert again["draft"] is not None


def test_model_failure_is_reported_not_raised(tools):
    class BrokenModel(ScriptedModel):
        async def stream(self, *args, **kwargs):
            raise RuntimeError("Error 002: Access to Bedrock models is not allowed for this account")
            yield  # pragma: no cover - makes this an async generator

    result = ask_guardian(BrokenModel([]), tools, "hello")

    assert result.answer == ""
    assert result.tools_called == []
    assert "Error 002" in result.error


def test_each_question_starts_a_fresh_conversation(tools):
    model = ScriptedModel([("text", "first"), ("text", "second")])

    ask_guardian(model, tools, "one")
    ask_guardian(model, tools, "two")

    assert len(model.calls[1]["messages"]) == 1


def test_trace_matches_the_real_tool_call_and_result(tools):
    model = ScriptedModel(
        [
            ("tool", "check_document_dates", {"i94_admit_until": "2026-11-03", "i797_valid_until": "2026-12-28"}),
            ("text", "They disagree by 55 days."),
        ]
    )

    result = ask_guardian(model, tools, "Do my documents disagree?")

    assert len(result.trace) == 1
    step = result.trace[0]
    assert step.step == 1
    assert step.tool == "check_document_dates"
    assert step.input == {"i94_admit_until": "2026-11-03", "i797_valid_until": "2026-12-28"}
    assert step.status == "success"
    assert step.tool_use_id == model.last_tool_result()["toolUseId"]
    assert step.mode is None and step.decision is None  # pure rule, no gate involved
    assert "55 day" in step.summary
    assert result.trace_dicts()[0]["tool"] == "check_document_dates"


def test_trace_carries_mode_gate_and_persistence_facts(tools):
    model = ScriptedModel([("tool", "run_sample_case_check", {}), ("text", "One thing needs review.")])

    step = ask_guardian(model, tools, "Check the sample case.").trace[0]

    assert step.mode == "recorded"
    assert step.decision == "surfaced"
    assert "novelty" in step.reason
    assert step.persisted_draft is True


def test_trace_records_tool_errors(tools):
    model = ScriptedModel([("tool", "check_visa_bulletin", {"month": "1999-01"}), ("text", "That month is not available.")])

    step = ask_guardian(model, tools, "What about January 1999?").trace[0]

    assert step.status == "error"
    assert step.input == {"month": "1999-01"}
    assert "no captured bulletin" in step.summary


def test_trace_is_empty_when_no_tool_was_called(tools):
    result = ask_guardian(ScriptedModel([("text", "I can only check documents, bulletins, and recalls.")]), tools, "hi")
    assert result.trace == [] and result.tools_called == []


def test_session_keeps_the_conversation_and_traces_only_the_new_turn(tools):
    from agent.llm.guardian import ask_in_session, build_guardian_agent

    model = ScriptedModel(
        [
            ("tool", "check_document_dates", {"i94_admit_until": "2026-11-03", "i797_valid_until": "2026-12-28"}),
            ("text", "They disagree by 55 days."),
            ("text", "Tell your attorney the I-94 ends 55 days before the I-797; a draft is ready."),
        ]
    )
    agent = build_guardian_agent(model, tools)

    first = ask_in_session(agent, "Do my documents disagree?")
    second = ask_in_session(agent, "What should I tell my attorney?")

    assert first.tools_called == ["check_document_dates"]
    assert second.tools_called == [] and second.trace == []  # no new tool call on the follow-up
    assert "55 days" in second.answer
    # The follow-up saw the whole conversation, including the earlier tool result.
    assert len(model.calls[-1]["messages"]) >= 4
    assert any("toolResult" in block for m in model.calls[-1]["messages"] for block in m.get("content", []))
