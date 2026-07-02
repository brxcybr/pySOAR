"""VirusTotal v3 analyzer plugin."""

from __future__ import annotations

import base64

import requests

from analyzers.base import AnalyzerBase, AnalyzerReport

_BASE = 'https://www.virustotal.com/api/v3'


class VirusTotalAnalyzer(AnalyzerBase):
    analyzer_id = 'virustotal'
    display_name = 'VirusTotal'
    supported_types = ('ip-dst', 'ip-src', 'domain', 'url', 'hash')
    min_interval_seconds = 16.0  # free tier: 4 lookups/minute

    def _endpoint(self, obs_type: str, value: str) -> str:
        if obs_type in ('ip-dst', 'ip-src'):
            return f'{_BASE}/ip_addresses/{value}'
        if obs_type == 'domain':
            return f'{_BASE}/domains/{value}'
        if obs_type == 'hash':
            return f'{_BASE}/files/{value}'
        if obs_type == 'url':
            url_id = base64.urlsafe_b64encode(value.encode()).decode().strip('=')
            return f'{_BASE}/urls/{url_id}'
        raise ValueError(f'unsupported type {obs_type}')

    def _analyze_live(self, obs_type: str, value: str) -> AnalyzerReport:
        response = requests.get(
            self._endpoint(obs_type, value),
            headers={'x-apikey': self.api_key},
            timeout=30,
        )
        if response.status_code == 404:
            return AnalyzerReport(
                self.analyzer_id, obs_type, value,
                verdict='unknown', summary='not found in VirusTotal',
            )
        response.raise_for_status()
        data = response.json().get('data', {})
        stats = data.get('attributes', {}).get('last_analysis_stats', {})
        malicious = int(stats.get('malicious', 0))
        suspicious = int(stats.get('suspicious', 0))
        total = sum(int(v) for v in stats.values()) or 1
        score = min(100.0, 100.0 * (malicious + 0.5 * suspicious) / total * 4)
        if malicious >= 3:
            verdict = 'malicious'
        elif malicious + suspicious >= 1:
            verdict = 'suspicious'
        else:
            verdict = 'benign'
        return AnalyzerReport(
            self.analyzer_id, obs_type, value,
            verdict=verdict,
            score=round(score, 1),
            summary=f'{malicious} malicious / {suspicious} suspicious of {total} engines',
            raw={'last_analysis_stats': stats},
        )
