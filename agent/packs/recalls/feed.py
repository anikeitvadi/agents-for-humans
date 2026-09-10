"""CPSC recall feed integration (C4): a live, no-auth API call with a
captured-but-real fallback for when the feed is unreachable during the
demo. Deliberately narrow — one known manufacturer, one recall — per
docs/architecture-spec.md's recall-to-remedy scope ("one source, one
seeded receipt, one match, one ping", not a general recall matcher).
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import httpx

CPSC_API_URL = "https://www.saferproducts.gov/RestWebServices/Recall"
FALLBACK_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "recalls" / "captured_cpsc_recall.json"

FeedMode = Literal["live", "fallback"]

_REMEDY_PATTERN = re.compile(r"(refund|voucher|credit)[^$]{0,40}\$(\d[\d,]*)", re.IGNORECASE)


@dataclass
class RecallItem:
    recall_id: str
    manufacturer: str
    product_name: str
    remedy_options: list[dict] = field(default_factory=list)
    source_url: str = ""
    recall_date: str = ""

    def as_dict(self) -> dict:
        return {
            "manufacturer": self.manufacturer,
            "product_name": self.product_name,
            "remedy_options": self.remedy_options,
        }


def load_fallback_recall() -> RecallItem:
    data = json.loads(FALLBACK_PATH.read_text())
    return RecallItem(
        recall_id=data["recall_id"],
        manufacturer=data["manufacturer"],
        product_name=data["product_name"],
        remedy_options=data["remedy_options"],
        source_url=data["source_url"],
        recall_date=data["recall_date"],
    )


def _extract_remedy_options(remedies: list[dict]) -> list[dict]:
    text = " ".join(r.get("Name", "") for r in remedies)
    options = []
    for kind, amount in _REMEDY_PATTERN.findall(text):
        kind_normalized = "refund" if kind.lower() == "credit" else kind.lower()
        options.append({"type": kind_normalized, "amount": int(amount.replace(",", ""))})
    return options


def _normalize_cpsc_item(item: dict, manufacturer: str) -> RecallItem | None:
    products = item.get("Products") or []
    if not products:
        return None
    full_name = (products[0].get("Name") or "").strip()
    if not full_name.lower().startswith(manufacturer.lower()):
        return None
    product_name = full_name[len(manufacturer):].strip()
    remedy_options = _extract_remedy_options(item.get("Remedies") or [])
    if not product_name or not remedy_options:
        return None
    return RecallItem(
        recall_id=str(item.get("RecallID", "")),
        manufacturer=manufacturer,
        product_name=product_name,
        remedy_options=remedy_options,
        source_url=item.get("URL", ""),
        recall_date=(item.get("RecallDate") or "")[:10],
    )


def fetch_live_recall(manufacturer: str = "Cambridge Audio", lookback_days: int = 365, timeout: float = 5.0) -> RecallItem | None:
    """Queries the live, no-auth CPSC recall API for the first recall whose
    product name starts with `manufacturer`. Returns None on any network,
    HTTP, parse, or shape failure — the caller falls back to the captured
    snapshot rather than crashing the demo."""
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    try:
        response = httpx.get(CPSC_API_URL, params={"format": "json", "RecallDateStart": start}, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not isinstance(data, list):
        return None

    for item in data:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_cpsc_item(item, manufacturer)
        if normalized is not None:
            return normalized
    return None


def get_recall_item(manufacturer: str = "Cambridge Audio", attempt_live: bool = True) -> tuple[RecallItem, FeedMode]:
    if attempt_live:
        live = fetch_live_recall(manufacturer)
        if live is not None:
            return live, "live"
    return load_fallback_recall(), "fallback"
