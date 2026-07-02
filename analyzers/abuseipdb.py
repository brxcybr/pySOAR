"""AbuseIPDB analyzer plugin (IP reputation)."""

from __future__ import annotations

import requests

from analyzers.base import AnalyzerBase, AnalyzerReport


class AbuseIpDbAnalyzer(AnalyzerBase):
    analyzer_id = 'abuseipdb'
    display_name = 'AbuseIPDB'
    supported_types = ('ip-dst', 'ip-src')
    min_interval_seconds = 2.0  # free tier: 1000/day

    def _analyze_live(self, obs_type: str, value: str) -> AnalyzerReport:
        response = requests.get(
            'https://api.abuseipdb.com/api/v2/check',
            params={'ipAddress': value, 'maxAgeInDays': 90},
            headers={'Key': self.api_key, 'Accept': 'application/json'},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json().get('data', {})
        confidence = float(data.get('abuseConfidenceScore', 0))
        if confidence >= 75:
            verdict = 'malicious'
        elif confidence >= 25:
            verdict = 'suspicious'
        else:
            verdict = 'benign'
        return AnalyzerReport(
            self.analyzer_id, obs_type, value,
            verdict=verdict,
            score=confidence,
            summary=(
                f'abuse confidence {confidence:.0f}%, '
                f"{data.get('totalReports', 0)} reports"
            ),
            raw={
                'abuseConfidenceScore': confidence,
                'totalReports': data.get('totalReports'),
                'countryCode': data.get('countryCode'),
                'isp': data.get('isp'),
            },
        )
