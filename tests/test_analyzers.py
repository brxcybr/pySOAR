#!/usr/bin/env python3

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from analyzers.base import AnalyzerBase, AnalyzerReport
from analyzers.registry import AnalyzerRegistry
from analyzers.runner import run_analyzers
from core.state_store import StateStore


class _EnvMock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='pysoar-analyzers-')
        self.env = patch.dict(os.environ, {
            'PYSOAR_MOCK_ANALYZERS': '1',
            'PYSOAR_STATE_DB': os.path.join(self.tmp, 'state.db'),
        })
        self.env.start()
        StateStore.reset()
        AnalyzerRegistry.reset()

    def tearDown(self):
        self.env.stop()
        StateStore.reset()
        AnalyzerRegistry.reset()


class TestAnalyzerFramework(_EnvMock):
    def test_registry_lists_default_analyzers(self):
        ids = [a['id'] for a in AnalyzerRegistry.get_instance().list_analyzers()]
        for expected in ('virustotal', 'abuseipdb', 'otx', 'shodan'):
            self.assertIn(expected, ids)

    def test_mock_verdicts_are_deterministic(self):
        analyzer = AnalyzerRegistry.get_instance().get('virustotal')
        bad = analyzer.analyze('ip-dst', '203.0.113.9')
        good = analyzer.analyze('ip-dst', '8.8.8.8')
        self.assertEqual(bad.verdict, 'malicious')
        self.assertEqual(good.verdict, 'benign')

    def test_reports_are_cached(self):
        analyzer = AnalyzerRegistry.get_instance().get('abuseipdb')
        first = analyzer.analyze('ip-dst', '203.0.113.9')
        second = analyzer.analyze('ip-dst', '203.0.113.9')
        self.assertFalse(first.cached)
        self.assertTrue(second.cached)
        self.assertEqual(first.verdict, second.verdict)

    def test_unsupported_type_reports_error(self):
        analyzer = AnalyzerRegistry.get_instance().get('shodan')
        report = analyzer.analyze('domain', 'example.com')
        self.assertTrue(report.error)

    def test_runner_enriches_shared_data(self):
        shared = {
            'observables': [
                {'type': 'ip-dst', 'value': '203.0.113.9', 'sources': [], 'enrichment': {}},
            ],
            'schema_version': 1,
        }
        reports = run_analyzers(shared)
        self.assertTrue(reports)
        enrichment = shared['observables'][0]['enrichment']
        self.assertIn('virustotal', enrichment)
        self.assertEqual(enrichment['virustotal']['verdict'], 'malicious')
        self.assertEqual(shared['analysis_verdict'], 'malicious')
        self.assertGreater(shared['analysis_max_score'], 50)

    def test_runner_analyzer_subset(self):
        shared = {
            'observables': [
                {'type': 'ip-dst', 'value': '8.8.8.8', 'sources': [], 'enrichment': {}},
            ],
            'schema_version': 1,
        }
        reports = run_analyzers(shared, analyzer_ids=['otx'])
        self.assertTrue(all(r.analyzer == 'otx' for r in reports))


class TestAnalyzeStep(_EnvMock):
    def test_analyze_step_in_playbook(self):
        from classes import PlaybookFunction, ConfigurationManager

        step = PlaybookFunction(
            name='analyze:virustotal',
            trigger={'type': 'always'},
            on_success='halt_playbook',
            on_fail='halt_playbook',
        )
        shared = {
            'observables': [
                {'type': 'ip-dst', 'value': '203.0.113.9', 'sources': [], 'enrichment': {}},
            ],
            'schema_version': 1,
        }
        result_shared, next_step = step.execute(shared, ConfigurationManager())
        self.assertEqual(next_step, 'halt_playbook')
        self.assertEqual(result_shared['analysis_verdict'], 'malicious')

    def test_expression_condition_after_analysis(self):
        from triggers import evaluate_condition

        shared = {'analysis_max_score': 90.0}
        self.assertTrue(
            evaluate_condition(
                {'type': 'expression', 'when': 'analysis_max_score >= 75'}, shared
            )
        )
        self.assertFalse(
            evaluate_condition(
                {'type': 'expression', 'when': 'analysis_max_score >= 95'}, shared
            )
        )


class TestLiveParsing(unittest.TestCase):
    """Verify provider response parsing with canned HTTP payloads."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='pysoar-live-')
        self.env = patch.dict(os.environ, {
            'PYSOAR_STATE_DB': os.path.join(self.tmp, 'state.db'),
            'PYSOAR_ANALYZER_VIRUSTOTAL_API_KEY': 'k',
            'PYSOAR_ANALYZER_ABUSEIPDB_API_KEY': 'k',
            'PYSOAR_MOCK_ANALYZERS': '',
        })
        self.env.start()
        StateStore.reset()

    def tearDown(self):
        self.env.stop()
        StateStore.reset()

    def _response(self, payload, status=200):
        response = MagicMock()
        response.status_code = status
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    @patch('analyzers.virustotal.requests.get')
    def test_virustotal_verdict_mapping(self, mock_get):
        from analyzers.virustotal import VirusTotalAnalyzer

        mock_get.return_value = self._response({
            'data': {'attributes': {'last_analysis_stats': {
                'malicious': 12, 'suspicious': 2, 'harmless': 60, 'undetected': 6,
            }}}
        })
        analyzer = VirusTotalAnalyzer()
        analyzer.min_interval_seconds = 0
        report = analyzer.analyze('ip-dst', '203.0.113.9')
        self.assertEqual(report.verdict, 'malicious')
        self.assertGreater(report.score, 30)

    @patch('analyzers.abuseipdb.requests.get')
    def test_abuseipdb_verdict_mapping(self, mock_get):
        from analyzers.abuseipdb import AbuseIpDbAnalyzer

        mock_get.return_value = self._response({
            'data': {'abuseConfidenceScore': 88, 'totalReports': 40, 'countryCode': 'ZZ'}
        })
        analyzer = AbuseIpDbAnalyzer()
        analyzer.min_interval_seconds = 0
        report = analyzer.analyze('ip-dst', '203.0.113.9')
        self.assertEqual(report.verdict, 'malicious')
        self.assertEqual(report.score, 88.0)

    @patch('analyzers.virustotal.requests.get')
    def test_provider_error_does_not_raise(self, mock_get):
        from analyzers.virustotal import VirusTotalAnalyzer

        mock_get.side_effect = ConnectionError('provider down')
        analyzer = VirusTotalAnalyzer()
        analyzer.min_interval_seconds = 0
        report = analyzer.analyze('ip-dst', '203.0.113.9')
        self.assertTrue(report.error)
        self.assertEqual(report.verdict, 'unknown')


if __name__ == '__main__':
    unittest.main()
