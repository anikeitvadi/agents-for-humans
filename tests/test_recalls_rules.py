from agent.packs.recalls.rules import match_recall_to_receipt

RECALL = {
    "manufacturer": "Cambridge Audio",
    "product_name": "Melomania Touch Earbuds",
    "remedy_options": [{"type": "refund", "amount": 218}, {"type": "voucher", "amount": 350}],
}


def test_matching_manufacturer_and_product_is_a_match():
    receipt = {"manufacturer": "Cambridge Audio", "product_name": "Melomania Touch Earbuds"}

    result = match_recall_to_receipt(RECALL, receipt)

    assert result.matched is True
    assert "218" in result.message
    assert "350" in result.message
    assert result.demo_scope is True


def test_match_is_case_insensitive():
    receipt = {"manufacturer": "cambridge audio", "product_name": "melomania touch earbuds"}

    result = match_recall_to_receipt(RECALL, receipt)

    assert result.matched is True


def test_different_manufacturer_is_not_a_match():
    receipt = {"manufacturer": "Sony", "product_name": "Melomania Touch Earbuds"}

    result = match_recall_to_receipt(RECALL, receipt)

    assert result.matched is False


def test_different_product_is_not_a_match():
    receipt = {"manufacturer": "Cambridge Audio", "product_name": "Some Other Product"}

    result = match_recall_to_receipt(RECALL, receipt)

    assert result.matched is False
