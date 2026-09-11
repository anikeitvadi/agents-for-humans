from unittest.mock import patch

import httpx

from agent.packs.recalls.feed import fetch_live_recall, get_recall_item, load_fallback_recall

_RAW_CPSC_ITEM = {
    "RecallID": 10948,
    "RecallDate": "2026-09-03T00:00:00",
    "URL": "https://cpsc.gov/Recalls/2026/Audio-Partnership-Recalls-Cambridge-Audio-Yoyo-M-Portable-Bluetooth-Speakers-Due-to-Fire-Hazard",
    "Products": [{"Name": "Cambridge Audio Yoyo (M) Portable Bluetooth Speakers"}],
    "Remedies": [
        {
            "Name": "Consumers should contact Audio Partnership for a full cash refund of $218 or Cambridge "
            "Audio online store voucher of $350."
        }
    ],
}

_UNRELATED_ITEM = {
    "RecallID": 1,
    "RecallDate": "2026-09-01T00:00:00",
    "URL": "https://cpsc.gov/Recalls/2026/some-other-recall",
    "Products": [{"Name": "Some Other Brand Toy"}],
    "Remedies": [{"Name": "Stop using the product immediately."}],
}


def test_load_fallback_recall_is_the_real_captured_cambridge_audio_recall():
    item = load_fallback_recall()

    assert item.manufacturer == "Cambridge Audio"
    assert "Yoyo" in item.product_name
    assert {"type": "refund", "amount": 218} in item.remedy_options
    assert {"type": "voucher", "amount": 350} in item.remedy_options


def test_fetch_live_recall_normalizes_manufacturer_product_and_remedies():
    with patch("agent.packs.recalls.feed.httpx.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = [_UNRELATED_ITEM, _RAW_CPSC_ITEM]

        item = fetch_live_recall(manufacturer="Cambridge Audio")

    assert item is not None
    assert item.manufacturer == "Cambridge Audio"
    assert item.product_name == "Yoyo (M) Portable Bluetooth Speakers"
    assert item.recall_id == "10948"
    assert {"type": "refund", "amount": 218} in item.remedy_options
    assert {"type": "voucher", "amount": 350} in item.remedy_options


def test_fetch_live_recall_returns_none_when_manufacturer_not_in_feed():
    with patch("agent.packs.recalls.feed.httpx.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = [_UNRELATED_ITEM]

        item = fetch_live_recall(manufacturer="Cambridge Audio")

    assert item is None


def test_fetch_live_recall_returns_none_on_network_error_not_a_crash():
    with patch("agent.packs.recalls.feed.httpx.get", side_effect=httpx.ConnectError("boom")):
        item = fetch_live_recall(manufacturer="Cambridge Audio")

    assert item is None


def test_fetch_live_recall_returns_none_on_malformed_response_not_a_crash():
    with patch("agent.packs.recalls.feed.httpx.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {"not": "a list"}

        item = fetch_live_recall(manufacturer="Cambridge Audio")

    assert item is None


def test_get_recall_item_uses_fallback_when_live_disabled():
    item, mode = get_recall_item(attempt_live=False)

    assert mode == "fallback"
    assert item.manufacturer == "Cambridge Audio"


def test_get_recall_item_uses_fallback_when_live_fetch_fails():
    with patch("agent.packs.recalls.feed.fetch_live_recall", return_value=None):
        item, mode = get_recall_item(attempt_live=True)

    assert mode == "fallback"


def test_get_recall_item_uses_live_when_fetch_succeeds():
    live_item = load_fallback_recall()
    with patch("agent.packs.recalls.feed.fetch_live_recall", return_value=live_item):
        item, mode = get_recall_item(attempt_live=True)

    assert mode == "live"
    assert item is live_item
