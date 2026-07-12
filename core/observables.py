"""Canonical observable schema v1 for playbook shared data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# MISP-aligned observable types used across playbooks.
STANDARD_OBSERVABLE_TYPES = frozenset({
    'ip-dst',
    'ip-src',
    'domain',
    'url',
    'hash',
    'email',
    'filename',
    'message',
})


@dataclass
class Observable:
    type: str
    value: str
    sources: list[str] = field(default_factory=list)
    enrichment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'value': self.value,
            'sources': list(self.sources),
            'enrichment': dict(self.enrichment),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Observable':
        return cls(
            type=data['type'],
            value=str(data['value']),
            sources=list(data.get('sources') or []),
            enrichment=dict(data.get('enrichment') or {}),
        )


class SharedDataContext:
    """Wraps playbook shared_data with observable v1 helpers."""

    SCHEMA_VERSION = 1

    def __init__(self, data: Optional[dict] = None):
        self._data = data if isinstance(data, dict) else {}

    @property
    def raw(self) -> dict:
        return self._data

    def ensure_schema(self) -> dict:
        self._data.setdefault('schema_version', self.SCHEMA_VERSION)
        self._data.setdefault('observables', [])
        return self._data

    def observables(self) -> list[Observable]:
        self.ensure_schema()
        return [Observable.from_dict(item) for item in self._data.get('observables', [])]

    def add_observable(
        self,
        obs_type: str,
        value: str,
        source: str = '',
        enrichment: Optional[dict] = None,
    ) -> None:
        self.ensure_schema()
        value = str(value).strip()
        if not value:
            return
        for existing in self._data['observables']:
            if existing.get('type') == obs_type and existing.get('value') == value:
                if source and source not in existing.setdefault('sources', []):
                    existing['sources'].append(source)
                if enrichment:
                    existing.setdefault('enrichment', {}).update(enrichment)
                self._sync_legacy_key(obs_type, value)
                return
        entry = Observable(
            type=obs_type,
            value=value,
            sources=[source] if source else [],
            enrichment=enrichment or {},
        )
        self._data['observables'].append(entry.to_dict())
        self._sync_legacy_key(obs_type, value)

    def _sync_legacy_key(self, obs_type: str, value: str) -> None:
        """Keep flat legacy keys (e.g. ip-dst) in sync for existing playbooks."""
        if obs_type not in STANDARD_OBSERVABLE_TYPES:
            return
        current = self._data.get(obs_type)
        if current is None:
            self._data[obs_type] = value
        elif isinstance(current, list):
            if value not in current:
                current.append(value)
        elif current != value:
            self._data[obs_type] = [current, value]

    def sync_from_legacy(self, source: str = '') -> None:
        """Promote flat observable keys into the observables list."""
        for obs_type in STANDARD_OBSERVABLE_TYPES:
            if obs_type not in self._data:
                continue
            raw = self._data[obs_type]
            if isinstance(raw, list):
                for item in raw:
                    self.add_observable(obs_type, item, source=source)
            elif raw is not None:
                self.add_observable(obs_type, raw, source=source)

    def values_for_type(self, obs_type: str) -> list[str]:
        values = []
        for obs in self.observables():
            if obs.type == obs_type:
                values.append(obs.value)
        legacy = self._data.get(obs_type)
        if legacy is None:
            return values
        if isinstance(legacy, list):
            values.extend(str(v) for v in legacy if str(v) not in values)
        elif str(legacy) not in values:
            values.append(str(legacy))
        return values

    def merge_enrichment(self, obs_type: str, value: str, analyzer: str, report: dict) -> None:
        self.ensure_schema()
        for item in self._data['observables']:
            if item.get('type') == obs_type and item.get('value') == value:
                item.setdefault('enrichment', {})[analyzer] = report
                return
        self.add_observable(
            obs_type,
            value,
            enrichment={analyzer: report},
        )


def wrap_shared_data(shared_data: Optional[dict]) -> SharedDataContext:
    ctx = SharedDataContext(shared_data)
    ctx.ensure_schema()
    return ctx
