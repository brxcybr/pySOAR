"""OPNsense firewall integration."""

import base64
import json

import requests

from classes import Log


class OpnsenseFunction:
    """Manage OPNsense firewall rules via the API."""

    def __init__(self, opnsense_init):
        self.log = Log.get_instance()
        self.url = opnsense_init.url.rstrip('/')
        self.api_key = opnsense_init.api_key
        self.ssl = opnsense_init.ssl
        self.verifycert = opnsense_init.verifycert
        self.default_interface = getattr(opnsense_init, 'default_interface', 'wan')
        if hasattr(opnsense_init, 'params'):
            cfg = opnsense_init.params.get('opnsense', {})
            self.default_interface = cfg.get('default_interface', self.default_interface)

    def _auth_header(self):
        token = base64.b64encode(self.api_key.encode()).decode()
        return {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json',
        }

    def _request(self, method, path, data=None):
        url = f"{self.url}{path}"
        verify = self.verifycert if self.ssl else False
        response = requests.request(
            method,
            url,
            headers=self._auth_header(),
            data=json.dumps(data) if data is not None else None,
            verify=verify,
            timeout=30,
        )
        if not response.ok:
            self.log.error(f"OPNsense API error {response.status_code}: {response.text}")
            return None
        if response.text:
            return response.json()
        return {}

    def get_firewall_status(self):
        return self._request('GET', '/api/core/system/status')

    def add_firewall_rule(self, src=None, interface=None, descr='PySOAR Generated Block Rule'):
        if src is None:
            src = []
        if not isinstance(src, list):
            src = [src]
        interface = interface or self.default_interface
        created = []
        for ip in src:
            rule = {
                "rule": {
                    "enabled": "1",
                    "action": "block",
                    "interface": interface,
                    "direction": "in",
                    "ipprotocol": "inet",
                    "protocol": "any",
                    "source_net": ip,
                    "destination_net": "any",
                    "description": descr,
                }
            }
            result = self._request('POST', '/api/firewall/filter/addRule', rule)
            if result:
                created.append(result)
                self.log.info(f"OPNsense block rule added for {ip}")
        if not created:
            return False
        self.apply_changes()
        return {"ip-dst": src, "opnsense-rule-uuid": created}

    def delete_firewall_rule(self, uuid):
        return self._request('POST', '/api/firewall/filter/delRule', {"uuid": uuid})

    def apply_changes(self):
        result = self._request('POST', '/api/firewall/filter/apply', {})
        return {"opnsense-firewall-status": bool(result)}
