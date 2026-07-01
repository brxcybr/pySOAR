"""CrowdSec Local API integration."""

import json

import requests

from classes import Log


class CrowdsecFunction:
    """Query and manage CrowdSec decisions via the Local API."""

    def __init__(self, crowdsec_init):
        self.log = Log.get_instance()
        self.url = crowdsec_init.url.rstrip('/')
        self.api_key = crowdsec_init.api_key
        self.ssl = crowdsec_init.ssl
        self.verifycert = crowdsec_init.verifycert

    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-Api-Key'] = self.api_key
        return headers

    def _request(self, method, path, data=None):
        url = f"{self.url}{path}"
        verify = self.verifycert if self.ssl else False
        response = requests.request(
            method,
            url,
            headers=self._headers(),
            data=json.dumps(data) if data is not None else None,
            verify=verify,
            timeout=30,
        )
        response.raise_for_status()
        if response.text:
            return response.json()
        return {}

    def list_decisions(self):
        """Return active CrowdSec decisions."""
        return self._request('GET', '/v1/decisions')

    def ban_ip(self, ip_dst=None, duration='4h', reason='PySOAR blocklist sync'):
        if not ip_dst:
            self.log.error("ban_ip requires ip-dst")
            return False
        targets = ip_dst if isinstance(ip_dst, list) else [ip_dst]
        created = []
        for ip in targets:
            payload = {
                "duration": duration,
                "reason": reason,
                "scope": "ip",
                "value": ip,
                "type": "ban",
            }
            result = self._request('POST', '/v1/decisions', payload)
            created.append(result)
            self.log.info(f"CrowdSec ban created for {ip}")
        return {"ip-dst": targets, "crowdsec-decision-id": created}

    def unban_ip(self, ip_dst=None):
        if not ip_dst:
            return False
        targets = ip_dst if isinstance(ip_dst, list) else [ip_dst]
        for ip in targets:
            self._request('DELETE', f'/v1/decisions/{ip}')
            self.log.info(f"CrowdSec ban removed for {ip}")
        return True

    def sync_blocklist(self, ip_dst=None, duration='4h'):
        """Ban all supplied indicators via CrowdSec."""
        if not ip_dst:
            self.log.warning("sync_blocklist called with no ip-dst values")
            return False
        return self.ban_ip(ip_dst=ip_dst, duration=duration)
