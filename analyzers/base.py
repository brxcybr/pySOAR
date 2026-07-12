"""Analyzer plugin contract.

Analyzers enrich a single observable (IP, domain, URL, hash, ...) with a
normalized verdict. Vendor services are plugins behind this contract; the
core never depends on any specific provider.

Free-tier friendliness is built into the base class:
- responses are cached in the persistent state store (default 1 hour)
- live calls are rate limited per analyzer (min interval between requests)
- mock mode (``PYSOAR_MOCK_ANALYZERS=1`` or a missing API key) returns
  deterministic canned verdicts so playbooks are testable offline
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

VERDICTS = ('unknown', 'benign', 'suspicious', 'malicious')


@dataclass
class AnalyzerReport:
    analyzer: str
    observable_type: str
    value: str
    verdict: str = 'unknown'
    score: float = 0.0  # 0..100, higher = more malicious
    summary: str = ''
    raw: dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    error: str = ''
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'analyzer': self.analyzer,
            'observable_type': self.observable_type,
            'value': self.value,
            'verdict': self.verdict,
            'score': self.score,
            'summary': self.summary,
            'raw': self.raw,
            'cached': self.cached,
            'error': self.error,
            'ts': self.ts,
        }


def mock_analyzers_enabled() -> bool:
    return os.environ.get('PYSOAR_MOCK_ANALYZERS', '').lower() in ('1', 'true', 'yes')


class AnalyzerBase(ABC):
    analyzer_id: str = ''
    display_name: str = ''
    supported_types: tuple = ('ip-dst', 'ip-src', 'domain', 'url', 'hash')
    cache_ttl_seconds: int = 3600
    min_interval_seconds: float = 15.0  # free-tier default (4 req/min)

    def __init__(self):
        self._last_live_call = 0.0

    # -- configuration --------------------------------------------------------

    @property
    def api_key(self) -> str:
        """API key from PYSOAR_ANALYZER_<ID>_API_KEY (vendor-agnostic scheme)."""
        env_name = f'PYSOAR_ANALYZER_{self.analyzer_id.upper()}_API_KEY'
        return os.environ.get(env_name, '').strip()

    @property
    def available(self) -> bool:
        return mock_analyzers_enabled() or bool(self.api_key)

    def supports(self, obs_type: str) -> bool:
        return obs_type in self.supported_types

    # -- main entry point ------------------------------------------------------

    def analyze(self, obs_type: str, value: str) -> AnalyzerReport:
        if not self.supports(obs_type):
            return AnalyzerReport(
                self.analyzer_id, obs_type, value,
                error=f'{self.analyzer_id} does not support {obs_type}',
            )

        cached = self._cache_get(obs_type, value)
        if cached is not None:
            return cached

        if mock_analyzers_enabled() or not self.api_key:
            report = self._mock_report(obs_type, value)
        else:
            self._respect_rate_limit()
            try:
                report = self._analyze_live(obs_type, value)
            except Exception as exc:  # network/provider failures must not kill playbooks
                report = AnalyzerReport(
                    self.analyzer_id, obs_type, value, error=str(exc)
                )
        if not report.error:
            self._cache_put(report)
        return report

    @abstractmethod
    def _analyze_live(self, obs_type: str, value: str) -> AnalyzerReport:
        """Query the provider. Only called with rate limiting applied."""

    # -- mock mode -------------------------------------------------------------

    def _mock_report(self, obs_type: str, value: str) -> AnalyzerReport:
        """Deterministic canned verdict: TEST-NET / example values are malicious."""
        malicious_markers = ('203.0.113.', '198.51.100.', 'evil', 'malware')
        is_bad = any(marker in value for marker in malicious_markers)
        return AnalyzerReport(
            self.analyzer_id,
            obs_type,
            value,
            verdict='malicious' if is_bad else 'benign',
            score=90.0 if is_bad else 5.0,
            summary=f'mock verdict from {self.analyzer_id}',
            raw={'mock': True},
        )

    # -- caching / rate limiting -----------------------------------------------

    def _cache_key(self, obs_type: str, value: str) -> str:
        return f'analyzer_cache:{self.analyzer_id}:{obs_type}:{value}'

    def _cache_get(self, obs_type: str, value: str) -> Optional[AnalyzerReport]:
        from core.state_store import StateStore

        entry = StateStore.get_instance().get_state(self._cache_key(obs_type, value))
        if not isinstance(entry, dict):
            return None
        if time.time() - float(entry.get('ts', 0)) > self.cache_ttl_seconds:
            return None
        report = AnalyzerReport(
            analyzer=self.analyzer_id,
            observable_type=obs_type,
            value=value,
            verdict=entry.get('verdict', 'unknown'),
            score=float(entry.get('score', 0.0)),
            summary=entry.get('summary', ''),
            raw=entry.get('raw') or {},
            cached=True,
            ts=float(entry.get('ts', 0)),
        )
        return report

    def _cache_put(self, report: AnalyzerReport):
        from core.state_store import StateStore

        StateStore.get_instance().set_state(
            self._cache_key(report.observable_type, report.value),
            {
                'verdict': report.verdict,
                'score': report.score,
                'summary': report.summary,
                'raw': report.raw,
                'ts': report.ts,
            },
        )

    def _respect_rate_limit(self):
        elapsed = time.time() - self._last_live_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_live_call = time.time()
