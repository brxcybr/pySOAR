#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock

from integrations.pfsense_functions import PfsenseFunction


class TestPfsenseInProcessMock(unittest.TestCase):
    def _mock_client(self):
        init = MagicMock()
        init.url = 'https://{PFSENSE_URL}'
        init.api_key = '{API_KEY}'
        init.ssl = False
        init.verifycert = False
        init.default_interface = 'wan'
        init.params = {'pfsense': {'default_interface': 'wan'}}
        return PfsenseFunction(init)

    def test_mock_add_firewall_rule(self):
        client = self._mock_client()
        result = client.add_firewall_rule(src=['203.0.113.99'])
        self.assertIsInstance(result, dict)
        self.assertIn('203.0.113.99', result.get('ip-dst', []))

    def test_mock_skips_duplicate_ip(self):
        client = self._mock_client()
        first = client.add_firewall_rule(src=['203.0.113.88'])
        self.assertIsInstance(first, dict)
        second = client.add_firewall_rule(src=['203.0.113.88'])
        self.assertTrue(second)
        self.assertIn('203.0.113.88', client._mock_blocked_ips)


if __name__ == '__main__':
    unittest.main()
