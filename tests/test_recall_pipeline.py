from agent.engine.store import Store
from agent.packs.recalls.feed import load_fallback_recall
from agent.packs.recalls.pipeline import run_recall_check


def _receipt(manufacturer="Cambridge Audio", product_name="Yoyo (M) Portable Bluetooth Speakers"):
    return {"receipt_id": "seeded-001", "manufacturer": manufacturer, "product_name": product_name, "purchase_date": "2024-06-01"}


def test_matched_receipt_surfaces_one_alert_with_remedy_draft(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    recall = load_fallback_recall()

    result = run_recall_check(store, clock_id="recall-clock", recall_item=recall, receipt=_receipt())

    assert result.match.matched is True
    assert result.alert.decision == "surfaced"
    assert result.draft is not None
    assert "218" in result.draft.body
    assert "350" in result.draft.body


def test_unmatched_receipt_produces_no_ping(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    recall = load_fallback_recall()

    result = run_recall_check(
        store, clock_id="recall-clock", recall_item=recall, receipt=_receipt(manufacturer="Sony", product_name="WF-1000XM5")
    )

    assert result.match.matched is False
    assert result.alert.decision == "silent"
    assert result.draft is None


def test_repeat_poll_same_receipt_produces_no_second_ping_but_keeps_draft(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    recall = load_fallback_recall()

    first = run_recall_check(store, clock_id="recall-clock", recall_item=recall, receipt=_receipt())
    second = run_recall_check(store, clock_id="recall-clock", recall_item=recall, receipt=_receipt())

    assert second.alert.decision == "silent"
    assert second.draft is not None
    assert second.draft.body == first.draft.body


def test_survives_restart_without_duplicate(tmp_path):
    db_path = tmp_path / "ledger.db"
    recall = load_fallback_recall()
    store = Store(str(db_path))
    first = run_recall_check(store, clock_id="recall-clock", recall_item=recall, receipt=_receipt())

    restarted_store = Store(str(db_path))
    replayed = run_recall_check(restarted_store, clock_id="recall-clock", recall_item=recall, receipt=_receipt())

    assert replayed.alert.decision == "silent"
    assert replayed.draft is not None
    assert replayed.draft.body == first.draft.body


def test_different_receipt_against_same_recall_is_a_distinct_event(tmp_path):
    # Two different seeded receipts matching the same recall must not
    # dedup against each other — each is its own event/alert.
    store = Store(str(tmp_path / "ledger.db"))
    recall = load_fallback_recall()
    receipt_a = _receipt()
    receipt_b = {**_receipt(), "receipt_id": "seeded-002"}

    first = run_recall_check(store, clock_id="recall-clock", recall_item=recall, receipt=receipt_a)
    second = run_recall_check(store, clock_id="recall-clock", recall_item=recall, receipt=receipt_b)

    assert first.alert.decision == "surfaced"
    assert second.alert.decision == "surfaced"
