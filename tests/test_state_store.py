#!/usr/bin/env python3

import tempfile
import time
import unittest
from pathlib import Path

from core.state_store import StateStore, action_fingerprint


class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = StateStore(path=str(Path(self.tmp.name) / 'state.db'))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_run_lifecycle(self):
        run_id = self.store.start_run('test-playbook')
        self.store.record_step(run_id, 'enable_threat_feed', success=True, next_step='get_event')
        self.store.record_step(run_id, 'get_event', success=False)
        self.store.end_run(run_id, 'failed', steps=2, cycles=0, shared_data={'ip-dst': '1.2.3.4'})

        run = self.store.get_run(run_id)
        self.assertEqual(run['status'], 'failed')
        self.assertEqual(run['steps'], 2)
        self.assertEqual(len(run['step_records']), 2)
        self.assertIn('1.2.3.4', run['shared_data'])

    def test_list_runs_filters_by_playbook(self):
        self.store.start_run('alpha')
        self.store.start_run('beta')
        runs = self.store.list_runs(playbook='alpha')
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['playbook'], 'alpha')

    def test_observable_memory_dedupes_and_counts(self):
        self.store.record_observable('ip-dst', '203.0.113.9', source='misp')
        self.store.record_observable('ip-dst', '203.0.113.9', source='sensor:beacon_detector')
        seen = self.store.seen_observable('ip-dst', '203.0.113.9')
        self.assertEqual(seen['times_seen'], 2)
        self.assertIn('misp', seen['sources'])
        self.assertIn('sensor:beacon_detector', seen['sources'])
        self.assertIsNone(self.store.seen_observable('ip-dst', '198.51.100.1'))

    def test_record_shared_data_observables(self):
        shared = {
            'observables': [
                {'type': 'ip-dst', 'value': '198.51.100.7'},
                {'type': 'domain', 'value': 'evil.example.com'},
            ]
        }
        self.store.record_shared_data_observables(shared, source='playbook')
        self.assertIsNotNone(self.store.seen_observable('domain', 'evil.example.com'))

    def test_action_ledger_window(self):
        fp = action_fingerprint('pfsense', 'add_firewall_rule', {'src': '1.2.3.4'})
        self.store.record_action(fp, 'add_firewall_rule', integration='pfsense')
        self.assertIsNotNone(self.store.recent_action(fp, window_seconds=60))
        self.assertIsNone(self.store.recent_action(fp, window_seconds=0))
        other = action_fingerprint('pfsense', 'add_firewall_rule', {'src': '5.6.7.8'})
        self.assertIsNone(self.store.recent_action(other, window_seconds=60))

    def test_fingerprint_is_stable_and_order_independent(self):
        a = action_fingerprint('x', 'f', {'a': 1, 'b': 2})
        b = action_fingerprint('x', 'f', {'b': 2, 'a': 1})
        self.assertEqual(a, b)

    def test_kv_state(self):
        self.store.set_state('baseline', {'mean': 4.2})
        self.assertEqual(self.store.get_state('baseline'), {'mean': 4.2})
        self.assertEqual(self.store.get_state('missing', 'default'), 'default')

    def test_mark_interrupted_runs(self):
        self.store.start_run('crashy')
        count = self.store.mark_interrupted_runs()
        self.assertEqual(count, 1)
        runs = self.store.list_runs(playbook='crashy')
        self.assertEqual(runs[0]['status'], 'interrupted')

    def test_disabled_store_is_noop(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {'PYSOAR_STATE_DB': 'off'}):
            store = StateStore()
        self.assertFalse(store.enabled)
        run_id = store.start_run('noop')
        self.assertTrue(run_id)  # still returns an id
        self.assertEqual(store.list_runs(), [])


if __name__ == '__main__':
    unittest.main()
