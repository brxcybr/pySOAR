"""Secure storage and retrieval of integration API keys."""

import base64
import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SECRETS_DIR = Path(os.environ.get('PYSOAR_SECRETS_DIR', 'secrets'))
VAULT_DIR = SECRETS_DIR / 'vault'
MASTER_KEY_FILE = SECRETS_DIR / '.master.key'
SALT_FILE = SECRETS_DIR / '.salt'
API_KEY_FIELD = 'api_key'


class SecretStoreError(Exception):
    """Raised when secret storage or retrieval fails."""


class SecretStore:
    """Encrypt integration credentials at rest and resolve them at runtime."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        from classes import Log

        self.log = Log.get_instance()
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet = None

    def _fernet_client(self):
        if self._fernet is None:
            self._fernet = Fernet(self._load_master_key())
        return self._fernet

    def _load_master_key(self):
        env_key = os.environ.get('PYSOAR_MASTER_KEY')
        if env_key:
            return env_key.encode()

        if MASTER_KEY_FILE.exists():
            return MASTER_KEY_FILE.read_bytes().strip()

        passphrase = os.environ.get('PYSOAR_SECRETS_PASSPHRASE')
        if passphrase:
            return self._derive_key_from_passphrase(passphrase)

        raise SecretStoreError(
            'No secrets master key found. Run `python pysoar.py --init-secrets` '
            'or set PYSOAR_MASTER_KEY / PYSOAR_SECRETS_PASSPHRASE.'
        )

    def _derive_key_from_passphrase(self, passphrase):
        if not SALT_FILE.exists():
            salt = os.urandom(16)
            SALT_FILE.write_bytes(salt)
            self._restrict_permissions(SALT_FILE)
        else:
            salt = SALT_FILE.read_bytes()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))

    @staticmethod
    def _restrict_permissions(path):
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def init_master_key(self, force=False):
        """Create a new Fernet master key file."""
        if MASTER_KEY_FILE.exists() and not force:
            self.log.info('Secrets master key already exists.')
            return str(MASTER_KEY_FILE)

        key = Fernet.generate_key()
        MASTER_KEY_FILE.write_bytes(key)
        self._restrict_permissions(MASTER_KEY_FILE)
        self._fernet = Fernet(key)
        self.log.info(f'Created secrets master key at {MASTER_KEY_FILE}')
        return str(MASTER_KEY_FILE)

    def _vault_path(self, integration_name):
        return VAULT_DIR / f'{integration_name}.json'

    def store_api_key(self, integration_name, api_key):
        if not api_key:
            raise SecretStoreError('Refusing to store an empty API key.')

        encrypted = self._fernet_client().encrypt(api_key.encode()).decode()
        payload = {API_KEY_FIELD: encrypted}
        path = self._vault_path(integration_name)
        path.write_text(json.dumps(payload, indent=2))
        self._restrict_permissions(path)
        self.log.info(f'Stored encrypted API key for integration {integration_name}.')

    def retrieve_api_key(self, integration_name):
        path = self._vault_path(integration_name)
        if not path.exists():
            raise SecretStoreError(
                f'No encrypted API key found for integration {integration_name}.'
            )

        payload = json.loads(path.read_text())
        encrypted = payload.get(API_KEY_FIELD)
        if not encrypted:
            raise SecretStoreError(
                f'Vault file for {integration_name} does not contain an API key.'
            )

        try:
            return self._fernet_client().decrypt(encrypted.encode()).decode()
        except InvalidToken as exc:
            raise SecretStoreError(
                f'Unable to decrypt API key for {integration_name}. '
                'Check PYSOAR_MASTER_KEY or PYSOAR_SECRETS_PASSPHRASE.'
            ) from exc

    def delete_api_key(self, integration_name):
        path = self._vault_path(integration_name)
        if path.exists():
            path.unlink()

    @staticmethod
    def _env_api_key(integration_name):
        return os.environ.get(f'PYSOAR_{integration_name.upper()}_API_KEY')

    @staticmethod
    def _is_placeholder(value):
        if not value:
            return True
        return '{' in str(value) and '}' in str(value)

    def resolve_api_key(self, integration_name, config):
        """Resolve an API key for configuration or execution."""
        env_value = self._env_api_key(integration_name)
        if env_value:
            self.log.debug(
                f'Using API key for {integration_name} from environment override.'
            )
            return env_value

        if config.get('api_key_secret'):
            return self.retrieve_api_key(integration_name)

        plaintext = config.get('api_key', '')
        if plaintext and not self._is_placeholder(plaintext):
            self.log.warning(
                f'Integration {integration_name} uses a plaintext API key in config. '
                'Run `python pysoar.py --migrate-secrets` to encrypt it.'
            )
            return plaintext

        return ''

    def mask_api_key(self, api_key):
        if not api_key:
            return '(not set)'
        if len(api_key) <= 4:
            return '****'
        return f'****{api_key[-4:]}'

    def prepare_config_for_save(self, integration_name, config_data):
        """Persist API key to vault and return YAML-safe config without plaintext."""
        prepared = dict(config_data)
        api_key = prepared.pop('api_key', '')
        if api_key:
            self.store_api_key(integration_name, api_key)
            prepared['api_key_secret'] = True
        elif prepared.get('api_key_secret'):
            prepared['api_key_secret'] = True
        else:
            prepared.pop('api_key_secret', None)
        return prepared

    def migrate_integration_config(self, integration_name, config_path='./config'):
        """Move plaintext api_key from YAML into the encrypted vault."""
        import yaml

        path = Path(config_path) / f'{integration_name}.yaml'
        if not path.exists():
            raise SecretStoreError(f'Config file not found: {path}')

        with path.open('r') as handle:
            data = yaml.safe_load(handle) or {}
        section = data.get(integration_name, {})
        if section.get('api_key_secret'):
            self.log.info(f'{integration_name}: already using encrypted secret storage.')
            return False

        plaintext = section.get('api_key', '')
        if not plaintext or self._is_placeholder(plaintext):
            self.log.warning(f'{integration_name}: no plaintext API key to migrate.')
            return False

        self.init_master_key()
        section = self.prepare_config_for_save(integration_name, section)
        data[integration_name] = section
        with path.open('w') as handle:
            yaml.safe_dump(data, handle, default_flow_style=False, sort_keys=False)
        self.log.info(f'{integration_name}: migrated API key to encrypted vault.')
        return True

    def migrate_all_integrations(self, config_path='./config'):
        """Migrate plaintext API keys for every integration config file."""
        migrated = []
        config_dir = Path(config_path)
        if not config_dir.exists():
            raise SecretStoreError(f'Config directory not found: {config_dir}')

        self.init_master_key()
        for path in sorted(config_dir.glob('*.yaml')):
            if path.name.endswith('.template.yaml'):
                continue
            integration_name = path.stem
            if self.migrate_integration_config(integration_name, config_path):
                migrated.append(integration_name)
        return migrated
