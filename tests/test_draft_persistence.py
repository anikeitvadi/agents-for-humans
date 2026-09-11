from agent.engine.store import Store


def _key():
    return dict(clock_id="c1", event_id="evt-1", rule_version="v1")


def test_save_then_get_draft_round_trips(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    saved = store.save_draft(**_key(), status="ready", subject="Subj", body="Body", used_llm_personalization=False)
    fetched = store.get_draft(**_key())

    assert saved is True
    assert fetched.status == "ready"
    assert fetched.subject == "Subj"
    assert fetched.body == "Body"
    assert fetched.used_llm_personalization is False


def test_get_draft_returns_none_when_absent(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))

    assert store.get_draft(**_key()) is None


def test_ready_draft_is_sticky_and_not_overwritten(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    store.save_draft(**_key(), status="ready", subject="Original", body="Original body", used_llm_personalization=False)

    overwritten = store.save_draft(**_key(), status="ready", subject="Different", body="Different body", used_llm_personalization=True)
    fetched = store.get_draft(**_key())

    assert overwritten is False
    assert fetched.subject == "Original"
    assert fetched.body == "Original body"


def test_failed_draft_can_be_retried_successfully(tmp_path):
    store = Store(str(tmp_path / "ledger.db"))
    store.save_draft(**_key(), status="failed", subject=None, body=None, used_llm_personalization=None)

    retried = store.save_draft(**_key(), status="ready", subject="Recovered", body="Recovered body", used_llm_personalization=False)
    fetched = store.get_draft(**_key())

    assert retried is True
    assert fetched.status == "ready"
    assert fetched.subject == "Recovered"


def test_draft_survives_restart(tmp_path):
    db_path = tmp_path / "ledger.db"
    store = Store(str(db_path))
    store.save_draft(**_key(), status="ready", subject="Subj", body="Body", used_llm_personalization=False)

    restarted_store = Store(str(db_path))
    fetched = restarted_store.get_draft(**_key())

    assert fetched is not None
    assert fetched.subject == "Subj"
