#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from core.observables import Observable, SharedDataContext
from core.manifests import ManifestRegistry, ActionManifest
from core.plugin_registry import PluginRegistry
from core.audit_log import AuditLog
from core.api_auth import verify_api_token, api_auth_enabled


class TestObservables(unittest.TestCase):
    def test_add_and_legacy_sync(self):
        ctx = SharedDataContext({})
        ctx.add_observable('ip-dst', '203.0.113.1', source='test')
        self.assertEqual(ctx.raw['ip-dst'], '203.0.113.1')
        self.assertEqual(len(ctx.observables()), 1)

    def test_sync_from_legacy_list(self):
        ctx = SharedDataContext({'ip-dst': ['203.0.113.1', '203.0.113.2']})
        ctx.sync_from_legacy(source='legacy')
        values = ctx.values_for_type('ip-dst')
        self.assertEqual(len(values), 2)


class TestManifestRegistry(unittest.TestCase):
    def setUp(self):
        ManifestRegistry.reset()

    def test_loads_bundled_manifests(self):
        registry = ManifestRegistry.get_instance()
        manifest = registry.get('add_firewall_rule')
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.integration, 'pfsense')
        self.assertEqual(manifest.risk, 'high')
        self.assertIn('ip-dst', manifest.input_mapping)

    def test_custom_manifest_dir(self):
        ManifestRegistry.reset()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'custom.yaml'
            path.write_text(yaml.safe_dump({
                'name': 'custom_action',
                'integration': 'test',
                'producer': True,
                'outputs': ['ip-dst'],
            }))
            registry = ManifestRegistry(Path(tmp))
            self.assertIsNotNone(registry.get('custom_action'))
            self.assertIn('custom_action', registry.producer_functions())


class TestPluginRegistry(unittest.TestCase):
    def setUp(self):
        PluginRegistry.reset()

    def test_loads_misp_plugin(self):
        registry = PluginRegistry.get_instance()
        cls = registry.get_class('misp')
        self.assertIsNotNone(cls)
        self.assertEqual(cls.__name__, 'MispFunction')

    def test_registered_names(self):
        names = PluginRegistry.get_instance().registered_names()
        self.assertIn('misp', names)
        self.assertIn('pfsense', names)


class TestAuditLog(unittest.TestCase):
    def test_writes_jsonl(self):
        AuditLog.reset()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'audit.jsonl'
            audit = AuditLog(path)
            audit.start_run('test', {'api_key': 'secret'})
            audit.step_end('add_firewall_rule', True, next_step='halt_playbook')
            audit.end_run('test', 'completed', steps=1)
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 3)
            payload = json.loads(lines[0])
            self.assertEqual(payload['event'], 'playbook_start')
            self.assertEqual(payload['metadata']['api_key'], '***')


class TestAPIAuth(unittest.TestCase):
    def test_disabled_when_no_token(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertFalse(api_auth_enabled())
            self.assertTrue(verify_api_token(None))

    def test_bearer_token(self):
        with patch.dict('os.environ', {'PYSOAR_API_TOKEN': 'test-token'}):
            self.assertTrue(api_auth_enabled())
            self.assertTrue(verify_api_token('Bearer test-token'))
            self.assertFalse(verify_api_token('Bearer wrong'))


class TestDispatchManifestIntegration(unittest.TestCase):
    def test_producer_functions_include_manifest(self):
        from integrations.dispatch import producer_functions

        producers = producer_functions()
        self.assertIn('get_misp_event_by_type', producers)
        self.assertIn('enable_threat_feed', producers)

    def test_input_mapping_from_manifest(self):
        from integrations.dispatch import function_input_mapping

        mapping = function_input_mapping()
        self.assertEqual(mapping['add_firewall_rule']['ip-dst'], 'src')


class TestListActionsCLI(unittest.TestCase):
    def test_list_actions_cli(self):
        from pysoar import list_actions_cli

        with patch('builtins.print') as mock_print:
            code = list_actions_cli()
        self.assertEqual(code, 0)
        self.assertTrue(mock_print.called)


if __name__ == '__main__':
    unittest.main()
