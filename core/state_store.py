"""SQLite-backed persistent state for runs, observables, and actions.

Designed for edge hardware (Raspberry Pi class): stdlib sqlite3 only,
WAL journaling, small batched writes, single file that survives restarts.
Disable with PYSOAR_STATE_DB=off; relocate with PYSOAR_STATE_DB=/path/db.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

_DISABLED_VALUES = ('0', 'false', 'no', 'off')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    playbook TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started REAL NOT NULL,
    ended REAL,
    steps INTEGER DEFAULT 0,
    cycles INTEGER DEFAULT 0,
    shared_data TEXT
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    function TEXT NOT NULL,
    success INTEGER NOT NULL,
    next_step TEXT,
    ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS observables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    times_seen INTEGER NOT NULL DEFAULT 1,
    sources TEXT NOT NULL DEFAULT '[]',
    UNIQUE(type, value)
);
CREATE TABLE IF NOT EXISTS actions (
    fingerprint TEXT PRIMARY KEY,
    integration TEXT,
    function TEXT NOT NULL,
    args TEXT,
    ts REAL NOT NULL,
    result TEXT
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_playbook ON runs(playbook, started);
"""


def action_fingerprint(integration: str, function: str, kwargs: Optional[dict] = None) -> str:
    """Stable fingerprint for an action invocation, used for idempotency."""
    canonical = json.dumps(
        {'integration': integration, 'function': function, 'kwargs': kwargs or {}},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class StateStore:
    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'StateStore':
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls):
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None

    def __init__(self, path: Optional[str] = None):
        env_value = os.environ.get('PYSOAR_STATE_DB', '')
        if path is not None:
            self.path = path
        elif env_value.lower() in _DISABLED_VALUES:
            self.path = None
        else:
            self.path = env_value or 'pysoar_state.db'
        self.enabled = self.path is not None
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        if self.enabled:
            self._connect()

    def _connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute('PRAGMA journal_mode=WAL')
        self._conn.execute('PRAGMA synchronous=NORMAL')
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _execute(self, sql: str, params: tuple = ()):
        if not self.enabled or self._conn is None:
            return None
        with self._lock:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        if not self.enabled or self._conn is None:
            return []
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    # -- runs ---------------------------------------------------------------

    def start_run(self, playbook: str, run_id: Optional[str] = None) -> str:
        run_id = run_id or str(uuid.uuid4())
        self._execute(
            'INSERT INTO runs (id, playbook, status, started) VALUES (?, ?, ?, ?)',
            (run_id, playbook, 'running', time.time()),
        )
        return run_id

    def end_run(
        self,
        run_id: str,
        status: str,
        steps: int = 0,
        cycles: int = 0,
        shared_data: Optional[dict] = None,
    ):
        self._execute(
            'UPDATE runs SET status = ?, ended = ?, steps = ?, cycles = ?, shared_data = ? WHERE id = ?',
            (
                status,
                time.time(),
                steps,
                cycles,
                json.dumps(shared_data, default=str) if shared_data is not None else None,
                run_id,
            ),
        )

    def record_step(self, run_id: str, function: str, success: bool, next_step: Optional[str] = None):
        self._execute(
            'INSERT INTO steps (run_id, function, success, next_step, ts) VALUES (?, ?, ?, ?, ?)',
            (run_id, function, 1 if success else 0, next_step, time.time()),
        )

    def list_runs(self, limit: int = 20, playbook: Optional[str] = None) -> list[dict]:
        if playbook:
            rows = self._query(
                'SELECT * FROM runs WHERE playbook = ? ORDER BY started DESC LIMIT ?',
                (playbook, limit),
            )
        else:
            rows = self._query('SELECT * FROM runs ORDER BY started DESC LIMIT ?', (limit,))
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> Optional[dict]:
        rows = self._query('SELECT * FROM runs WHERE id = ?', (run_id,))
        if not rows:
            return None
        run = dict(rows[0])
        run['step_records'] = [
            dict(row) for row in self._query('SELECT * FROM steps WHERE run_id = ? ORDER BY ts', (run_id,))
        ]
        return run

    def mark_interrupted_runs(self) -> int:
        """Mark runs left 'running' by a crash/power cut as interrupted."""
        cursor = self._execute(
            "UPDATE runs SET status = 'interrupted', ended = ? WHERE status = 'running'",
            (time.time(),),
        )
        return cursor.rowcount if cursor is not None else 0

    # -- observables ---------------------------------------------------------

    def record_observable(self, obs_type: str, value: str, source: str = ''):
        if not self.enabled or not value:
            return
        now = time.time()
        with self._lock:
            row = self._conn.execute(
                'SELECT id, sources, times_seen FROM observables WHERE type = ? AND value = ?',
                (obs_type, value),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    'INSERT INTO observables (type, value, first_seen, last_seen, times_seen, sources)'
                    ' VALUES (?, ?, ?, ?, 1, ?)',
                    (obs_type, value, now, now, json.dumps([source] if source else [])),
                )
            else:
                sources = json.loads(row['sources'] or '[]')
                if source and source not in sources:
                    sources.append(source)
                self._conn.execute(
                    'UPDATE observables SET last_seen = ?, times_seen = ?, sources = ? WHERE id = ?',
                    (now, row['times_seen'] + 1, json.dumps(sources), row['id']),
                )
            self._conn.commit()

    def record_shared_data_observables(self, shared_data: Optional[dict], source: str = ''):
        for item in (shared_data or {}).get('observables', []) or []:
            if isinstance(item, dict) and item.get('value'):
                self.record_observable(item.get('type', 'generic'), str(item['value']), source=source)

    def seen_observable(self, obs_type: str, value: str) -> Optional[dict]:
        rows = self._query(
            'SELECT * FROM observables WHERE type = ? AND value = ?', (obs_type, value)
        )
        return dict(rows[0]) if rows else None

    def list_observables(self, obs_type: Optional[str] = None, limit: int = 100) -> list[dict]:
        if obs_type:
            rows = self._query(
                'SELECT * FROM observables WHERE type = ? ORDER BY last_seen DESC LIMIT ?',
                (obs_type, limit),
            )
        else:
            rows = self._query('SELECT * FROM observables ORDER BY last_seen DESC LIMIT ?', (limit,))
        return [dict(row) for row in rows]

    # -- actions (idempotency ledger) -----------------------------------------

    def record_action(
        self,
        fingerprint: str,
        function: str,
        integration: str = '',
        kwargs: Optional[dict] = None,
        result: Any = None,
    ):
        self._execute(
            'INSERT OR REPLACE INTO actions (fingerprint, integration, function, args, ts, result)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (
                fingerprint,
                integration,
                function,
                json.dumps(kwargs or {}, default=str),
                time.time(),
                json.dumps(result, default=str) if result is not None else None,
            ),
        )

    def recent_action(self, fingerprint: str, window_seconds: int) -> Optional[dict]:
        """Return the ledger entry if this exact action ran within the window."""
        rows = self._query('SELECT * FROM actions WHERE fingerprint = ?', (fingerprint,))
        if not rows:
            return None
        entry = dict(rows[0])
        if time.time() - entry['ts'] > window_seconds:
            return None
        return entry

    # -- key/value state (sensor baselines etc.) ------------------------------

    def set_state(self, key: str, value: Any):
        self._execute(
            'INSERT OR REPLACE INTO kv (key, value, updated) VALUES (?, ?, ?)',
            (key, json.dumps(value, default=str), time.time()),
        )

    def get_state(self, key: str, default: Any = None) -> Any:
        rows = self._query('SELECT value FROM kv WHERE key = ?', (key,))
        if not rows:
            return default
        try:
            return json.loads(rows[0]['value'])
        except (TypeError, json.JSONDecodeError):
            return default
