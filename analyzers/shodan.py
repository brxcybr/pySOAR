"""Shodan analyzer plugin (host exposure context)."""

from __future__ import annotations

import requests

from analyzers.base import AnalyzerBase, AnalyzerReport


class ShodanAnalyzer(AnalyzerBase):
    analyzer_id = 'shodan'
    display_name = 'Shodan'
    supported_types = ('ip-dst', 'ip-src')
    min_interval_seconds = 2.0

    def _analyze_live(self, obs_type: str, value: str) -> AnalyzerReport:
        response = requests.get(
            f'https://api.shodan.io/shodan/host/{value}',
            params={'key': self.api_key, 'minify': True},
            timeout=30,
        )
        if response.status_code == 404:
            return AnalyzerReport(
                self.analyzer_id, obs_type, value,
                verdict='unknown', summary='host not indexed by Shodan',
            )
        response.raise_for_status()
        data = response.json()
        ports = data.get('ports') or []
        vulns = data.get('vulns') or []
        # Shodan is context, not reputation: exposure raises suspicion only.
        score = min(100.0, len(vulns) * 15 + len(ports) * 2)
        verdict = 'suspicious' if vulns else 'unknown'
        return AnalyzerReport(
            self.analyzer_id, obs_type, value,
            verdict=verdict,
            score=float(score),
            summary=f'{len(ports)} open port(s), {len(vulns)} known vuln(s)',
            raw={
                'ports': ports,
                'vulns': list(vulns),
                'org': data.get('org'),
                'os': data.get('os'),
            },
        )
