"""Recall-to-receipt matching — the thin generality-proof pack
(docs/architecture-spec.md §7). Deliberately NOT a general-purpose fuzzy
matcher: exact manufacturer + product-name match only. This is demo-scope
by design (a pre-staged recall + matching receipt), labeled as such so it
is never mistaken for a robust matcher that works on arbitrary receipts.
"""

from dataclasses import dataclass


@dataclass
class RecallMatchResult:
    matched: bool
    message: str
    demo_scope: bool = True


def match_recall_to_receipt(recall_item: dict, receipt: dict) -> RecallMatchResult:
    manufacturer_match = recall_item["manufacturer"].strip().lower() == receipt["manufacturer"].strip().lower()
    product_match = recall_item["product_name"].strip().lower() == receipt["product_name"].strip().lower()

    if not (manufacturer_match and product_match):
        return RecallMatchResult(matched=False, message="No recall match found for this receipt.")

    options = ", ".join(f"{o['type']} ${o['amount']}" for o in recall_item["remedy_options"])
    message = (
        f"Recall matched to your receipt for {recall_item['product_name']}: choose from {options}. "
        f"(Demo-scope exact match — not a general-purpose fuzzy matcher.)"
    )
    return RecallMatchResult(matched=True, message=message)
