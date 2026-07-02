"""Optional JSONL audit log for playbook execution."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

SENSITIVE_KEYS = frozenset({
    'api_key',
    'password',
    'token',
    'secret',
    'authorization',
})


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: '***' if key.lower() in SENSITIVE_KEYS else _redact(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class AuditLog:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self, path: Optional[Path] = None):
        env_path = os.environ.get('PYSOAR_AUDIT_LOG', '')
        if path is not None:
            self.path = path
        elif env_path.lower() in ('0', 'false', 'no', 'off', ''):
            self.path = None
        else:
            self.path = Path(env_path or 'PySOAR.audit.jsonl')
        self.enabled = self.path is not None
        self._run_id: Optional[str] = None

    def _write(self, event: str, payload: dict):
        if not self.enabled or self.path is None:
            return
        record = {
            'ts': time.time(),
            'event': event,
            'run_id': self._run_id,
            **payload,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, default=str) + '\n')

    def start_run(self, playbook: str, metadata: Optional[dict] = None):
        self._run_id = str(uuid.uuid4())
        self._write('playbook_start', {
            'playbook': playbook,
            'metadata': _redact(metadata or {}),
        })
        return self._run_id

    def end_run(self, playbook: str, status: str, steps: int = 0, cycles: int = 0):
        self._write('playbook_end', {
            'playbook': playbook,
            'status': status,
            'steps': steps,
            'cycles': cycles,
        })
        self._run_id = None

    def step_start(self, function: str, shared_data: Optional[dict] = None):
        self._write('step_start', {
            'function': function,
            'shared_data_keys': list((shared_data or {}).keys()),
        })

    def step_end(
        self,
        function: str,
        success: bool,
        next_step: Optional[str] = None,
        shared_data: Optional[dict] = None,
    ):
        self._write('step_end', {
            'function': function,
            'success': success,
            'next_step': next_step,
            'shared_data': _redact(shared_data or {}),
        })

    def step_error(self, function: str, error: str):
        self._write('step_error', {
            'function': function,
            'error': error,
        })
