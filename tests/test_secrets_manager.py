#!/usr/bin/env python3

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

import secrets_manager as sm
from secrets_manager import SecretStore, SecretStoreError


class TestSecretStore(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.config_dir = self.root / 'config'
        self.config_dir.mkdir()
        sm.SECRETS_DIR = self.root / 'secrets'
        sm.VAULT_DIR = sm.SECRETS_DIR / 'vault'
        sm.MASTER_KEY_FILE = sm.SECRETS_DIR / '.master.key'
        sm.SALT_FILE = sm.SECRETS_DIR / '.salt'
        SecretStore._instance = None
        self.mock_log = MagicMock()
        patcher = patch('classes.Log.get_instance', return_value=self.mock_log)
        self.addCleanup(patcher.stop)
        patcher.start()

    def _write_config(self, integration_name, section):
        path = self.config_dir / f'{integration_name}.yaml'
        with path.open('w') as handle:
            yaml.safe_dump({integration_name: section}, handle)
        return path

    def test_init_master_key_creates_file(self):
        store = SecretStore.get_instance()
        path = store.init_master_key()
        self.assertTrue(Path(path).exists())
        self.assertEqual(oct(Path(path).stat().st_mode & 0o777), '0o600')

    def test_store_and_retrieve_api_key(self):
        store = SecretStore.get_instance()
        store.init_master_key()
        store.store_api_key('misp', 'super-secret-key')
        self.assertEqual(store.retrieve_api_key('misp'), 'super-secret-key')
        vault = sm.VAULT_DIR / 'misp.json'
        self.assertTrue(vault.exists())
        payload = json.loads(vault.read_text())
        self.assertNotEqual(payload['api_key'], 'super-secret-key')

    def test_prepare_config_for_save_moves_key_to_vault(self):
        store = SecretStore.get_instance()
        store.init_master_key()
        prepared = store.prepare_config_for_save(
            'pfsense',
            {'url': 'https://fw.local', 'api_key': 'abc123'},
        )
        self.assertTrue(prepared.get('api_key_secret'))
        self.assertNotIn('api_key', prepared)
        self.assertEqual(store.retrieve_api_key('pfsense'), 'abc123')

    def test_resolve_api_key_prefers_environment_override(self):
        store = SecretStore.get_instance()
        store.init_master_key()
        store.store_api_key('misp', 'vault-key')
        with patch.dict(os.environ, {'PYSOAR_MISP_API_KEY': 'env-key'}):
            resolved = store.resolve_api_key(
                'misp',
                {'api_key_secret': True},
            )
        self.assertEqual(resolved, 'env-key')

    def test_resolve_api_key_warns_on_plaintext(self):
        store = SecretStore.get_instance()
        resolved = store.resolve_api_key(
            'misp',
            {'api_key': 'plaintext-key'},
        )
        self.assertEqual(resolved, 'plaintext-key')
        self.mock_log.warning.assert_called()

    def test_migrate_integration_config(self):
        store = SecretStore.get_instance()
        self._write_config(
            'misp',
            {'enabled': True, 'url': 'https://misp.local', 'api_key': 'migrate-me'},
        )
        migrated = store.migrate_integration_config('misp', str(self.config_dir))
        self.assertTrue(migrated)
        with (self.config_dir / 'misp.yaml').open() as handle:
            data = yaml.safe_load(handle)
        self.assertTrue(data['misp']['api_key_secret'])
        self.assertNotIn('api_key', data['misp'])
        self.assertEqual(store.retrieve_api_key('misp'), 'migrate-me')

    def test_mask_api_key(self):
        store = SecretStore.get_instance()
        self.assertEqual(store.mask_api_key('abcdefghij'), '****ghij')
        self.assertEqual(store.mask_api_key(''), '(not set)')

    def test_retrieve_missing_key_raises(self):
        store = SecretStore.get_instance()
        store.init_master_key()
        with self.assertRaises(SecretStoreError):
            store.retrieve_api_key('missing')


class TestIntegrationSecrets(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.config_dir = self.root / 'config'
        self.config_dir.mkdir()
        sm.SECRETS_DIR = self.root / 'secrets'
        sm.VAULT_DIR = sm.SECRETS_DIR / 'vault'
        sm.MASTER_KEY_FILE = sm.SECRETS_DIR / '.master.key'
        sm.SALT_FILE = sm.SECRETS_DIR / '.salt'
        SecretStore._instance = None
        self.mock_log = MagicMock()
        patcher = patch('classes.Log.get_instance', return_value=self.mock_log)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_integration_loads_encrypted_api_key(self):
        from classes import Integration

        store = SecretStore.get_instance()
        store.init_master_key()
        store.store_api_key('misp', 'encrypted-value')
        config_path = self.config_dir / 'misp.yaml'
        with config_path.open('w') as handle:
            yaml.safe_dump(
                {
                    'misp': {
                        'enabled': True,
                        'url': 'https://misp.local',
                        'api_key_secret': True,
                        'ssl': False,
                        'verifycert': False,
                        'accepts': ['ip-dst'],
                        'returns': ['ip-dst'],
                        'playbook_functions': ['get_misp_event_by_type'],
                    }
                },
                handle,
            )

        with patch.object(Integration, 'CONFIG_PATH', str(self.config_dir)):
            integration = Integration('misp')
        self.assertEqual(integration.api_key, 'encrypted-value')
        self.assertTrue(integration.api_key_secret)
        self.assertEqual(integration.masked_api_key, '****alue')


if __name__ == '__main__':
    unittest.main()
