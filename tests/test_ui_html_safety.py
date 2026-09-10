import re
from pathlib import Path

_UI_SOURCE = (Path(__file__).parent.parent / "ui" / "index.html").read_text()
# Matches every inline <script>...</script> block regardless of attributes
# (e.g. type="module", needed for ESM imports) — a <script src="..."> tag
# for an external library has no inline body and won't match here, since
# F5's concern is our own authored code, not a third-party library's.
_INLINE_SCRIPTS = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", _UI_SOURCE, re.DOTALL)
_ALL_INLINE_JS = "\n".join(_INLINE_SCRIPTS)
# Strip comments before scanning so documentation that merely *mentions*
# innerHTML (explaining why the code avoids it) doesn't trip the check below.
_CODE_ONLY = re.sub(r"//.*?$|/\*.*?\*/", "", _ALL_INLINE_JS, flags=re.MULTILINE | re.DOTALL)


def test_no_innerhtml_usage_in_inline_scripts():
    """API/model text (draft body, evidence, gate reasons, recall messages)
    must never be inserted via innerHTML — a returned string containing
    markup would be parsed and executed by the browser (F5). This app's own
    script never needs innerHTML at all: dynamic content always goes through
    textContent/text nodes (see the `el()` helper), so the safest guarantee
    is that innerHTML never appears in our inline script's actual code.
    """
    assert ".innerHTML" not in _CODE_ONLY, "inline script uses innerHTML — dynamic content must use textContent instead"


def test_dynamic_content_rendering_uses_textcontent():
    """Smoke check that dynamic rendering logic actually exists (guards
    against this file accidentally losing all its rendering code while
    trivially satisfying the innerHTML-free check above)."""
    assert _ALL_INLINE_JS.count("textContent") >= 5
