"""SQLite-backed persistence for the clock ledger. Uniqueness constraints
enforce replay-safe deduplication of events and alerts across restarts —
polling the same feed twice, or restarting the process, must not produce
duplicate alerts.
"""

import json
import sqlite3
from dataclasses import dataclass

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

CREATE TABLE IF NOT EXISTS drafts (
    clock_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    status TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    used_llm_personalization INTEGER,
    PRIMARY KEY (clock_id, event_id, rule_version)
);
"""


@dataclass
class DraftRecord:
    status: str  # "ready" | "failed"
    subject: str | None
    body: str | None
    used_llm_personalization: bool | None


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

    def save_draft(
        self,
        clock_id: str,
        event_id: str,
        rule_version: str,
        status: str,
        subject: str | None,
        body: str | None,
        used_llm_personalization: bool | None,
    ) -> bool:
        """Upsert a draft's lifecycle state (C2). A "ready" row is sticky —
        never overwritten — so a caller can always retrieve the original
        draft on reload/restart. A "failed" row is not sticky, so a retry
        that succeeds can replace it; a retry that fails again is a no-op,
        not a silently lost action.
        """
        used_llm_personalization_int = None if used_llm_personalization is None else int(used_llm_personalization)
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO drafts (clock_id, event_id, rule_version, status, subject, body, used_llm_personalization)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (clock_id, event_id, rule_version) DO UPDATE SET
                    status = excluded.status,
                    subject = excluded.subject,
                    body = excluded.body,
                    used_llm_personalization = excluded.used_llm_personalization
                WHERE drafts.status != 'ready'
                """,
                (clock_id, event_id, rule_version, status, subject, body, used_llm_personalization_int),
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return False

    def get_draft(self, clock_id: str, event_id: str, rule_version: str) -> DraftRecord | None:
        row = self._conn.execute(
            "SELECT status, subject, body, used_llm_personalization FROM drafts "
            "WHERE clock_id = ? AND event_id = ? AND rule_version = ?",
            (clock_id, event_id, rule_version),
        ).fetchone()
        if row is None:
            return None
        return DraftRecord(
            status=row[0],
            subject=row[1],
            body=row[2],
            used_llm_personalization=None if row[3] is None else bool(row[3]),
        )

    def list_alerts(self, clock_id: str) -> list[Alert]:
        rows = self._conn.execute(
            "SELECT clock_id, event_id, rule_version, decision, reason FROM alerts WHERE clock_id = ?",
            (clock_id,),
        ).fetchall()
        return [
            Alert(clock_id=r[0], event_id=r[1], rule_version=r[2], decision=r[3], reason=r[4])
            for r in rows
        ]
