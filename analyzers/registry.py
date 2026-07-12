"""Analyzer registry with entry-point discovery.

Third parties add analyzers without touching PySOAR core:

    [project.entry-points."pysoar.analyzers"]
    myanalyzer = "mypackage.analyzers:MyAnalyzer"
"""

from __future__ import annotations

from typing import Optional

from analyzers.base import AnalyzerBase

try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points  # type: ignore


class AnalyzerRegistry:
    _instance = None

    @classmethod
    def get_instance(cls) -> 'AnalyzerRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self):
        self._analyzers: dict[str, AnalyzerBase] = {}
        self._register_defaults()
        self._load_entry_points()

    def _register_defaults(self):
        from analyzers.abuseipdb import AbuseIpDbAnalyzer
        from analyzers.otx import OtxAnalyzer
        from analyzers.shodan import ShodanAnalyzer
        from analyzers.virustotal import VirusTotalAnalyzer

        for analyzer in (
            VirusTotalAnalyzer(),
            AbuseIpDbAnalyzer(),
            OtxAnalyzer(),
            ShodanAnalyzer(),
        ):
            self.register(analyzer)

    def _load_entry_points(self):
        try:
            eps = entry_points(group='pysoar.analyzers')
        except TypeError:
            eps = entry_points().get('pysoar.analyzers', [])
        for ep in eps:
            try:
                self.register(ep.load()())
            except Exception:
                continue

    def register(self, analyzer: AnalyzerBase):
        self._analyzers[analyzer.analyzer_id] = analyzer

    def get(self, analyzer_id: str) -> Optional[AnalyzerBase]:
        return self._analyzers.get(analyzer_id)

    def for_type(self, obs_type: str) -> list[AnalyzerBase]:
        return [a for a in self._analyzers.values() if a.supports(obs_type)]

    def list_analyzers(self) -> list[dict]:
        return [
            {
                'id': analyzer.analyzer_id,
                'name': analyzer.display_name,
                'types': list(analyzer.supported_types),
                'available': analyzer.available,
            }
            for analyzer in sorted(self._analyzers.values(), key=lambda a: a.analyzer_id)
        ]
