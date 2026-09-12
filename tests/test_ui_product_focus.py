"""Regression tests for the product restructure (2026-09-10 user feedback):
recall removed from the primary UI (backend/tests untouched — see
tests/test_recall_pipeline.py, tests/test_recalls_rules.py, etc.), the demo
rebuilt around one connected immigration story (upload -> review discrepancy
-> replay a bulletin update), and the R7/R8 UI-recovery/accessibility fixes.
Static source checks only — this repo has no JS test runner; see HANDOFF.md
for the browser click-through that verifies actual behavior.
"""

import re
from pathlib import Path

_UI_SOURCE = (Path(__file__).parent.parent / "ui" / "index.html").read_text()
_INLINE_SCRIPTS = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", _UI_SOURCE, re.DOTALL)
_ALL_INLINE_JS = "\n".join(_INLINE_SCRIPTS)


def test_no_recall_tab_or_recall_content_in_the_primary_ui():
    lowered = _UI_SOURCE.lower()
    for needle in ("recall demo", "tab-recall", "panel-recall", "recall-btn", "run recall demo", "/api/recalls/check"):
        assert needle not in lowered, f"recall content still present in the primary UI: {needle!r}"


def test_recall_backend_module_is_untouched_by_the_ui_change():
    # UI-only removal — the recall pack's implementation must still exist
    # and be reachable, even though nothing in ui/index.html calls it.
    from agent.packs.recalls.pipeline import run_recall_check  # noqa: F401


def test_upload_inputs_exist_for_all_three_sample_documents():
    for key in ("i94", "i797", "passport"):
        assert f'id="upload-{key}"' in _UI_SOURCE, f"missing upload input for {key}"
        assert f"type=\"file\"" in _UI_SOURCE


def test_sample_document_download_links_point_at_the_real_download_endpoint():
    for key in ("i94", "i797", "passport"):
        assert f"/api/sample-documents/{key}" in _UI_SOURCE


def test_upload_flow_posts_to_the_single_process_documents_endpoint():
    assert "/api/process-documents" in _ALL_INLINE_JS
    # R2: the old two-call (GET evidence, then POST decision) pattern must
    # be gone — one extraction produces both.
    assert "/api/sample-case" not in _ALL_INLINE_JS
    assert "/api/process-sample-case" not in _ALL_INLINE_JS


def test_bulletin_replay_story_beat_is_still_present():
    assert "/api/bulletin-poll" in _ALL_INLINE_JS


def test_mode_labels_distinguish_live_from_recorded():
    assert "live" in _ALL_INLINE_JS.lower()
    assert "recorded" in _ALL_INLINE_JS.lower()


def test_no_lawful_status_or_unlawful_presence_language():
    lowered = _UI_SOURCE.lower()
    for needle in ("lawful status", "unlawful presence", "f-1", "opt ", "status bar"):
        assert needle not in lowered, f"out-of-scope status language present: {needle!r}"


def test_review_section_reset_is_unconditional_not_only_on_the_error_path():
    # R7: the comparison must be restorable after an error -> success
    # recovery, not left permanently display:none. Requires a reset
    # function that runs before branching on the result, not one that only
    # exists inside the error branch.
    #
    # A prior version of this test searched for the bare substring
    # "resetReviewSection()", which also matches inside the function's own
    # signature ("function resetReviewSection() {") — it could pass even if
    # the function were never actually invoked anywhere. This distinguishes
    # the definition (ends in "{") from a real call (ends in ";").
    assert re.search(r"function\s+resetReviewSection\s*\(\s*\)\s*\{", _ALL_INLINE_JS), "resetReviewSection must be defined"

    invocation_pattern = re.compile(r"(?<!function )resetReviewSection\s*\(\s*\)\s*;")
    invocations = [m.start() for m in invocation_pattern.finditer(_ALL_INLINE_JS)]
    assert invocations, "resetReviewSection() must actually be invoked somewhere, not only defined"

    first_error_branch_index = _ALL_INLINE_JS.index("if (result.error)")
    assert any(call_site < first_error_branch_index for call_site in invocations), (
        "resetReviewSection() must be invoked before the error/success branch, not only inside it"
    )


def test_draft_overlay_uses_inert_when_closed_for_keyboard_safety():
    # R8: a closed drawer must not be keyboard-focusable — opacity/
    # pointer-events alone (the old bug) leave the Close button tabbable.
    assert "inert" in _ALL_INLINE_JS


def test_draft_overlay_moves_and_restores_focus():
    # R8: opening must move focus into the dialog; closing must restore it
    # to whatever triggered the open.
    assert ".focus()" in _ALL_INLINE_JS
    assert "lastFocused" in _ALL_INLINE_JS or "returnFocus" in _ALL_INLINE_JS


def test_comparison_documents_have_keyboard_activation_not_just_a_click_handler():
    # R8: role="button" + tabindex without a keydown handler is not
    # actually operable from the keyboard.
    assert "comparison-doc-i94" in _UI_SOURCE
    assert "'Enter'" in _ALL_INLINE_JS or '"Enter"' in _ALL_INLINE_JS


def test_no_innerhtml_usage_in_inline_scripts():
    code_only = re.sub(r"//.*?$|/\*.*?\*/", "", _ALL_INLINE_JS, flags=re.MULTILINE | re.DOTALL)
    assert ".innerHTML" not in code_only


def test_ask_guardian_endpoint_and_submission_ref_are_wired():
    assert "/api/ask" in _ALL_INLINE_JS
    assert "submission_ref" in _ALL_INLINE_JS
    # The guardian's own bundled-sample suggestion and the recall-oriented
    # suggestion from the pre-restructure UI must not reappear here.
    assert "speaker" not in _ALL_INLINE_JS.lower()


def test_approve_for_attorney_review_is_wired_to_the_draft_panel():
    assert "/api/drafts/approve" in _ALL_INLINE_JS
    assert "draft-approve-btn" in _UI_SOURCE
    assert "already_approved" in _ALL_INLINE_JS


def test_reset_endpoint_is_wired():
    assert "/api/reset" in _ALL_INLINE_JS
    assert 'id="reset-btn"' in _UI_SOURCE


def test_bulletin_replay_states_it_is_a_separate_case_from_the_upload():
    # Product polish note: the bulletin beat evaluates a different seeded
    # case than whatever was just uploaded, and must say so rather than
    # implying continuity with the upload above.
    assert "priority_date" in _ALL_INLINE_JS
    assert "separate" in _ALL_INLINE_JS.lower()


def test_apifetch_supports_formdata_without_json_stringifying_it():
    # F5/F6: a FormData body (the multipart upload) must never be
    # JSON.stringify'd, and must not get an explicit Content-Type (the
    # browser sets the multipart boundary itself).
    assert "instanceof FormData" in _ALL_INLINE_JS
    apifetch_start = _ALL_INLINE_JS.index("async function apiFetch")
    apifetch_body = _ALL_INLINE_JS[apifetch_start : apifetch_start + 1200]
    assert "isFormData" in apifetch_body


def test_sample_download_failure_cannot_populate_a_file_input():
    # F6: fetchSampleBlob must reject on a non-ok response before any File
    # object is constructed from it, so a failed download can't silently
    # become a "selected" file.
    fetch_start = _ALL_INLINE_JS.index("async function fetchSampleBlob")
    fetch_body = _ALL_INLINE_JS[fetch_start : fetch_start + 400]
    assert "response.ok" in fetch_body
    assert "throw new Error" in fetch_body


def test_upload_controls_are_disabled_during_processing():
    # F5: selection must be locked while a submission is in flight, not
    # just guarded after the fact by a version check.
    assert "setUploadControlsDisabled" in _ALL_INLINE_JS
    assert "uploadVersion" in _ALL_INLINE_JS


def test_load_bundled_sample_shortcut_exists_and_processes():
    assert 'id="load-bundled-btn"' in _UI_SOURCE
    shortcut_start = _ALL_INLINE_JS.index("loadBundledBtn.addEventListener")
    shortcut_body = _ALL_INLINE_JS[shortcut_start : shortcut_start + 600]
    assert "processDocuments()" in shortcut_body
