import re
from pathlib import Path

_UI_SOURCE = (Path(__file__).parent.parent / "ui" / "index.html").read_text()
_SCRIPT = _UI_SOURCE.split("<script>", 1)[1].split("</script>", 1)[0]


def test_innerhtml_assignments_never_interpolate_dynamic_content():
    """API/model text (draft body, evidence, gate reasons, recall messages)
    must never be inserted via innerHTML — a returned string containing
    markup would be parsed and executed by the browser (F5). Dynamic values
    belong in textContent/text nodes; innerHTML may only hold static markup.
    """
    template_literal_assignments = re.findall(r"\.innerHTML\s*=\s*`(.*?)`", _SCRIPT, re.DOTALL)
    for literal in template_literal_assignments:
        assert "${" not in literal, f"innerHTML assignment interpolates a value: {literal!r}"


def test_html_like_draft_text_renders_literally_not_as_markup():
    """Simulate what the browser's DOM would do with a draft body containing
    HTML-like text, using Node's DOM-less string-building absence as a proxy:
    assert the script sets textContent (never innerHTML) wherever draft
    subject/body, evidence, or message fields are rendered.
    """
    for dynamic_field in ("result.draft.body", "result.draft.subject", "result.alert.reason",
                           "matched.message", "unmatched.message"):
        assert dynamic_field in _SCRIPT, f"expected {dynamic_field} to still be rendered somewhere"
    # None of those fields' rendering lines may go through innerHTML.
    for line in _SCRIPT.splitlines():
        if "innerHTML" in line:
            for dynamic_field in ("result.draft.body", "result.draft.subject", "result.alert.reason",
                                   "matched.message", "unmatched.message", "fields[key]", "fields.evidence"):
                assert dynamic_field not in line, f"{dynamic_field} is rendered via innerHTML: {line.strip()}"
