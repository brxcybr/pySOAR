"""Shared integration helpers and base contract."""

import os


def use_mock_mode(integration_init):
    """Return True when integrations should run without live API calls."""
    if os.environ.get('PYSOAR_MOCK_INTEGRATIONS', '').lower() in ('1', 'true', 'yes'):
        return True
    url = getattr(integration_init, 'url', '') or ''
    api_key = getattr(integration_init, 'api_key', '') or ''
    return '{' in str(url) or '{' in str(api_key)


def config_looks_placeholder(value):
    if not value:
        return True
    return '{' in str(value) and '}' in str(value)


class IntegrationBase:
    """Minimal contract for PySOAR integration function classes."""

    integration_name = ''

    def __init__(self, integration_init):
        self._integration_init = integration_init
        self._mock = use_mock_mode(integration_init)

    @property
    def mock_mode(self):
        return self._mock

    def health_probe_path(self):
        """Optional HTTP path for connectivity checks."""
        return None
