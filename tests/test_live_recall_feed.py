"""Live CPSC feed check — excluded from the default `pytest -q` run (see
pyproject.toml's `-m "not live"` addopts) so the offline suite never
depends on network access. Run explicitly with:

    .venv/bin/python -m pytest -m live tests/test_live_recall_feed.py

Proves the real saferproducts.gov API is reachable and still contains the
Cambridge Audio recall the captured fallback snapshot represents — the
fallback is not itself proof the live feed still works (C4).
"""

import pytest

from agent.packs.recalls.feed import fetch_live_recall

pytestmark = pytest.mark.live


def test_live_cpsc_feed_returns_the_cambridge_audio_recall():
    item = fetch_live_recall(manufacturer="Cambridge Audio")

    assert item is not None
    assert "Yoyo" in item.product_name
    assert any(o["type"] == "refund" for o in item.remedy_options)
