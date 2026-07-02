#!/usr/bin/env python3

import unittest

from core.ingest import normalize_alert


class TestNormalizeAlert(unittest.TestCase):
    def test_flat_observable_keys(self):
        shared = normalize_alert({'ip-dst': '203.0.113.9', 'severity': 'high'})
        values = [o['value'] for o in shared['observables']]
        self.assertIn('203.0.113.9', values)
        self.assertEqual(shared['alert']['severity'], 'high')

    def test_observables_list(self):
        shared = normalize_alert({
            'observables': [
                {'type': 'domain', 'value': 'evil.example.com'},
                {'type': 'hash', 'value': 'd41d8cd98f00b204e9800998ecf8427e'},
            ],
        })
        types = {o['type'] for o in shared['observables']}
        self.assertEqual(types, {'domain', 'hash'})

    def test_stix_bundle(self):
        shared = normalize_alert({
            'type': 'bundle',
            'objects': [{'type': 'ipv4-addr', 'value': '198.51.100.7'}],
        })
        values = [o['value'] for o in shared['observables']]
        self.assertIn('198.51.100.7', values)
        self.assertIn('cidm_bundle', shared)

    def test_list_valued_flat_keys(self):
        shared = normalize_alert({'ip-dst': ['1.2.3.4', '5.6.7.8']})
        values = [o['value'] for o in shared['observables']]
        self.assertEqual(sorted(values), ['1.2.3.4', '5.6.7.8'])

    def test_non_dict_rejected(self):
        with self.assertRaises(ValueError):
            normalize_alert([1, 2, 3])

    def test_alert_source_recorded(self):
        shared = normalize_alert({'ip-dst': '1.2.3.4'}, source='suricata')
        self.assertEqual(shared['alert_source'], 'suricata')


class TestIngestApi(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient  # noqa: F401
        except ImportError:
            self.skipTest('fastapi not installed')

    def test_ingest_normalize_endpoint(self):
        from unittest.mock import MagicMock

        from fastapi.testclient import TestClient

        from api_server import create_app

        cm = MagicMock()
        pm = cm.playbook_mgr
        pm.playbook_names = ['triage']
        client = TestClient(create_app(cm))

        response = client.post('/ingest', json={'ip-dst': '203.0.113.9'})
        self.assertEqual(response.status_code, 200)
        values = [o['value'] for o in response.json()['observables']]
        self.assertIn('203.0.113.9', values)

    def test_ingest_launch_endpoint(self):
        from unittest.mock import MagicMock

        from fastapi.testclient import TestClient

        from api_server import create_app

        cm = MagicMock()
        pm = cm.playbook_mgr
        pm.playbook_names = ['triage']
        client = TestClient(create_app(cm))

        response = client.post(
            '/ingest/triage?background=false', json={'ip-dst': '203.0.113.9'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'completed')
        self.assertTrue(pm.launch_playbook.called)
        kwargs = pm.launch_playbook.call_args.kwargs
        self.assertTrue(kwargs['initial_shared_data']['observables'])

    def test_ingest_unknown_playbook_404(self):
        from unittest.mock import MagicMock

        from fastapi.testclient import TestClient

        from api_server import create_app

        cm = MagicMock()
        cm.playbook_mgr.playbook_names = []
        client = TestClient(create_app(cm))
        response = client.post('/ingest/ghost', json={'ip-dst': '1.1.1.1'})
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
