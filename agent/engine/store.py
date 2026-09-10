"""SQLite-backed persistence for the clock ledger. Uniqueness constraints
enforce replay-safe deduplication of events and alerts across restarts —
polling the same feed twice, or restarting the process, must not produce
duplicate alerts.
"""

import json
import sqlite3

from agent.engine.schema import Alert, Event

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    clock_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (clock_id, event_id, rule_version)
);
"""


class Store:
    def __init__(self, db_path: str):
        # check_same_thread=False: callers (e.g. FastAPI's sync-endpoint
        # threadpool) may invoke this Store from a different thread than
        # the one that constructed it. Safe here because the demo app
        # does not perform concurrent writes to the same Store.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save_event(self, event: Event) -> bool:
        try:
            self._conn.execute(
                "INSERT INTO events (event_id, source, effective_date, rule_version, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.source,
                    event.effective_date,
                    event.rule_version,
                    json.dumps(event.payload),
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Rollback releases the write lock the failed INSERT left open on
            # this connection — otherwise a later connection (e.g. a
            # restarted process reopening the same file) hangs waiting on it.
            self._conn.rollback()
            return False

    def save_alert(self, alert: Alert) -> bool:
        """Insert a new alert row, or claim an existing one's transition.

        A prior "silent" row for the same (clock_id, event_id, rule_version)
        key must be updatable to "surfaced" once the outcome changes —
        otherwise the transition can never be persisted and novelty
        suppression never engages (see F3). Once a row is "surfaced" it is
        sticky: the WHERE guard below refuses to overwrite it, so only one
        caller ever claims the surfaced alert and it is never downgraded.
        """
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO alerts (clock_id, event_id, rule_version, decision, reason)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (clock_id, event_id, rule_version) DO UPDATE SET
                    decision = excluded.decision,
                    reason = excluded.reason
                WHERE alerts.decision != 'surfaced' AND alerts.decision != excluded.decision
                """,
                (alert.clock_id, alert.event_id, alert.rule_version, alert.decision, alert.reason),
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return False

    def list_alerts(self, clock_id: str) -> list[Alert]:
        rows = self._conn.execute(
            "SELECT clock_id, event_id, rule_version, decision, reason FROM alerts WHERE clock_id = ?",
            (clock_id,),
        ).fetchall()
        return [
            Alert(clock_id=r[0], event_id=r[1], rule_version=r[2], decision=r[3], reason=r[4])
            for r in rows
        ]
