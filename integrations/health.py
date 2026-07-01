"""Integration health and readiness checks."""

import os
from dataclasses import dataclass

import requests


@dataclass
class HealthResult:
    healthy: bool
    integration: str
    message: str
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


def _config_looks_placeholder(value):
    if not value:
        return True
    return '{' in str(value) and '}' in str(value)


def check_integration_config(integration):
    """Validate integration config is present and not a template placeholder."""
    if not integration.enabled:
        return HealthResult(False, integration.name, 'Integration is disabled in config.')
    if _config_looks_placeholder(integration.url):
        return HealthResult(
            False,
            integration.name,
            'Integration URL is still a template placeholder.',
        )
    if _config_looks_placeholder(integration.api_key):
        return HealthResult(
            False,
            integration.name,
            'Integration API key is still a template placeholder.',
        )
    return HealthResult(True, integration.name, 'Configuration looks usable.')


def check_integration_connectivity(integration, timeout=5):
    """Best-effort live probe. Uses mock mode shortcuts when configured."""
    config_result = check_integration_config(integration)
    if not config_result.healthy:
        return config_result

    if os.environ.get('PYSOAR_MOCK_INTEGRATIONS', '').lower() in ('1', 'true', 'yes'):
        return HealthResult(True, integration.name, 'Mock integrations mode enabled.')

    if integration.name == 'misp':
        return _probe_http(integration, path='/servers/getVersion', integration_name='misp')
    if integration.name in ('pfsense', 'opnsense'):
        return _probe_http(integration, path='/api/v1/status/system', integration_name=integration.name)
    if integration.name == 'crowdsec':
        return _probe_http(integration, path='/v1/decisions', integration_name='crowdsec')
    if integration.name == 'webhook':
        return HealthResult(True, integration.name, 'Webhook URL configured; delivery verified at runtime only.')

    return HealthResult(True, integration.name, 'No dedicated probe; config validated only.')


def _probe_http(integration, path, integration_name):
    url = integration.url.rstrip('/') + path
    headers = {}
    if integration.api_key and integration_name != 'opnsense':
        headers['Authorization'] = integration.api_key
    if integration_name == 'crowdsec':
        headers['X-Api-Key'] = integration.api_key
    verify = integration.verifycert if integration.ssl else False
    try:
        response = requests.get(url, headers=headers, verify=verify, timeout=5)
        if response.ok:
            return HealthResult(True, integration_name, f'Reachable (HTTP {response.status_code}).')
        return HealthResult(
            False,
            integration_name,
            f'HTTP {response.status_code}: {response.text[:120]}',
        )
    except requests.RequestException as exc:
        return HealthResult(False, integration_name, f'Connection failed: {exc}')


def check_playbook_integrations(config_mgr, playbook):
    """Run config + connectivity checks for all playbook integration dependencies."""
    results = []
    enabled = {item.name: item for item in config_mgr.enabled_integrations}
    for integration_name in playbook.integration_deps or []:
        integration = enabled.get(integration_name)
        if not integration:
            results.append(
                HealthResult(False, integration_name, 'Integration is not enabled.')
            )
            continue
        config_result = check_integration_config(integration)
        results.append(config_result)
        if config_result.healthy:
            results.append(check_integration_connectivity(integration))
    return results


def summarize_health(results):
    unhealthy = [r for r in results if not r.healthy]
    if not unhealthy:
        return 'All required integrations passed health checks.'
    return '; '.join(f'{r.integration}: {r.message}' for r in unhealthy)
