"""AlienVault OTX analyzer plugin."""

from __future__ import annotations

import requests

from analyzers.base import AnalyzerBase, AnalyzerReport

_BASE = 'https://otx.alienvault.com/api/v1/indicators'

_SECTION_BY_TYPE = {
    'ip-dst': 'IPv4',
    'ip-src': 'IPv4',
    'domain': 'domain',
    'url': 'url',
    'hash': 'file',
}


class OtxAnalyzer(AnalyzerBase):
    analyzer_id = 'otx'
    display_name = 'AlienVault OTX'
    supported_types = tuple(_SECTION_BY_TYPE)
    min_interval_seconds = 2.0

    def _analyze_live(self, obs_type: str, value: str) -> AnalyzerReport:
        section = _SECTION_BY_TYPE[obs_type]
        response = requests.get(
            f'{_BASE}/{section}/{value}/general',
            headers={'X-OTX-API-KEY': self.api_key},
            timeout=30,
        )
        if response.status_code == 404:
            return AnalyzerReport(
                self.analyzer_id, obs_type, value,
                verdict='unknown', summary='not found in OTX',
            )
        response.raise_for_status()
        data = response.json()
        pulses = data.get('pulse_info', {}).get('count', 0)
        score = min(100.0, float(pulses) * 10)
        if pulses >= 5:
            verdict = 'malicious'
        elif pulses >= 1:
            verdict = 'suspicious'
        else:
            verdict = 'benign'
        return AnalyzerReport(
            self.analyzer_id, obs_type, value,
            verdict=verdict,
            score=score,
            summary=f'{pulses} OTX pulse(s) reference this indicator',
            raw={'pulse_count': pulses},
        )
