"""SQLite-backed persistence for the clock ledger. Uniqueness constraints
enforce replay-safe deduplication of events and alerts across restarts —
polling the same feed twice, or restarting the process, must not produce
duplicate alerts.
"""

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

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

CREATE TABLE IF NOT EXISTS action_receipts (
    clock_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    action_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (clock_id, event_id, rule_version, action_type)
);
"""


@dataclass
class DraftRecord:
    status: str  # "ready" | "failed"
    subject: str | None
    body: str | None
    used_llm_personalization: bool | None


@dataclass
class ActionReceipt:
    """Proof that a human took an action on a specific clock/event/rule
    version. Idempotent: the first record wins, repeats return it."""

    clock_id: str
    event_id: str
    rule_version: str
    action_type: str
    created_at: str  # ISO-8601 UTC
    already_recorded: bool = False


class ResetEpochMismatch(RuntimeError):
    """Raised when a reset happened while this caller's work was still in
    flight. The caller captured the epoch before starting slow work (e.g. a
    Bedrock call); by the time it tries to persist, reset() has already wiped
    the ledger and moved the epoch forward. Writing anyway would silently
    recreate rows the user just asked to clear — the caller must abort
    instead and report a controlled "reset during processing" outcome."""


class Store:
    def __init__(self, db_path: str):
        # check_same_thread=False: callers (e.g. FastAPI's sync-endpoint
        # threadpool) may invoke this Store from a different thread than
        # the one that constructed it. Safe here because the demo app
        # does not perform concurrent writes to the same Store.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        # The app shares one Store (one connection) across FastAPI's
        # threadpool-executed request handlers (check_same_thread=False
        # above permits this). A single sqlite3 connection object is not
        # safe for concurrent statement execution from multiple threads —
        # this lock serializes access to it (R5's "isolate transactions on
        # the app's shared SQLite connection"). It does not, and cannot,
        # serialize *separate* connections/processes sharing the same
        # database file — that atomicity comes from save_alert's/
        # save_draft's own guarded UPSERTs, which callers must respect
        # (see agent/engine/engine.py::process_event/ensure_draft).
        self._lock = threading.Lock()
        # Bumped by reset(); a caller that captured the epoch before slow
        # work (a Bedrock call) began can check it still matches before
        # writing, so an in-flight request cannot recreate rows just after
        # a reset cleared them (see reset()/*_epoch_guard below).
        self._epoch = 0

    def current_epoch(self) -> int:
        with self._lock:
            return self._epoch

    def _check_epoch_locked(self, expected_epoch: int | None) -> None:
        """Must be called while holding self._lock, immediately before a
        write, so the epoch check and the write are atomic together."""
        if expected_epoch is not None and expected_epoch != self._epoch:
            raise ResetEpochMismatch(
                f"reset occurred while this work was in flight (epoch {expected_epoch} -> {self._epoch})"
            )

    def save_event(self, event: Event, *, expected_epoch: int | None = None) -> bool:
        with self._lock:
            self._check_epoch_locked(expected_epoch)
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

    def get_event(self, event_id: str) -> Event | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT event_id, source, effective_date, rule_version, payload FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return Event(event_id=row[0], source=row[1], effective_date=row[2], rule_version=row[3], payload=json.loads(row[4]))

    def save_alert(self, alert: Alert, *, expected_epoch: int | None = None) -> bool:
        """Insert a new alert row, or claim an existing one's transition.

        A prior "silent" row for the same (clock_id, event_id, rule_version)
        key must be updatable to "surfaced" once the outcome changes —
        otherwise the transition can never be persisted and novelty
        suppression never engages (see F3). Once a row is "surfaced" it is
        sticky: the WHERE guard below refuses to overwrite it, so only one
        caller ever claims the surfaced alert and it is never downgraded.
        """
        with self._lock:
            self._check_epoch_locked(expected_epoch)
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
        *,
        expected_epoch: int | None = None,
    ) -> bool:
        """Upsert a draft's lifecycle state (C2). A "ready" row is sticky —
        never overwritten — so a caller can always retrieve the original
        draft on reload/restart. A "failed" row is not sticky, so a retry
        that succeeds can replace it; a retry that fails again is a no-op,
        not a silently lost action.
        """
        used_llm_personalization_int = None if used_llm_personalization is None else int(used_llm_personalization)
        with self._lock:
            self._check_epoch_locked(expected_epoch)
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
        with self._lock:
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

    def record_action(self, clock_id: str, event_id: str, rule_version: str, action_type: str) -> ActionReceipt:
        """Insert-once: a second call for the same key returns the original
        receipt with already_recorded=True and changes nothing."""
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self._lock:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO action_receipts (clock_id, event_id, rule_version, action_type, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (clock_id, event_id, rule_version, action_type, now),
            )
            self._conn.commit()
            # Read while still holding the lock: record_action() calling the
            # public get_action() (which also acquires self._lock) would
            # deadlock on this non-reentrant lock, so read via the unlocked
            # helper instead (see get_action below).
            receipt = self._get_action_locked(clock_id, event_id, rule_version, action_type)
            assert receipt is not None
            receipt.already_recorded = cursor.rowcount == 0
            return receipt

    def _get_action_locked(self, clock_id: str, event_id: str, rule_version: str, action_type: str) -> ActionReceipt | None:
        """Must be called while already holding self._lock."""
        row = self._conn.execute(
            "SELECT created_at FROM action_receipts "
            "WHERE clock_id = ? AND event_id = ? AND rule_version = ? AND action_type = ?",
            (clock_id, event_id, rule_version, action_type),
        ).fetchone()
        if row is None:
            return None
        return ActionReceipt(
            clock_id=clock_id, event_id=event_id, rule_version=rule_version, action_type=action_type, created_at=row[0]
        )

    def get_action(self, clock_id: str, event_id: str, rule_version: str, action_type: str) -> ActionReceipt | None:
        with self._lock:
            return self._get_action_locked(clock_id, event_id, rule_version, action_type)

    def reset(self) -> None:
        """Wipe the demo ledger (events, alerts, drafts, receipts) and bump
        the epoch so any processing already in flight aborts instead of
        recreating rows after this returns (see ResetEpochMismatch)."""
        with self._lock:
            self._epoch += 1
            for table in ("events", "alerts", "drafts", "action_receipts"):
                self._conn.execute(f"DELETE FROM {table}")
            self._conn.commit()

    def list_alerts(self, clock_id: str) -> list[Alert]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT clock_id, event_id, rule_version, decision, reason FROM alerts WHERE clock_id = ?",
                (clock_id,),
            ).fetchall()
        return [
            Alert(clock_id=r[0], event_id=r[1], rule_version=r[2], decision=r[3], reason=r[4])
            for r in rows
        ]

    def get_alert(self, clock_id: str, event_id: str, rule_version: str) -> Alert | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT clock_id, event_id, rule_version, decision, reason FROM alerts "
                "WHERE clock_id = ? AND event_id = ? AND rule_version = ?",
                (clock_id, event_id, rule_version),
            ).fetchone()
        if row is None:
            return None
        return Alert(clock_id=row[0], event_id=row[1], rule_version=row[2], decision=row[3], reason=row[4])
