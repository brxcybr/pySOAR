#!/usr/bin/env python3

import json
import unittest
from unittest.mock import MagicMock

import responses

from integrations.pfsense_functions import PfsenseFunction


class TestPfsenseMockAPI(unittest.TestCase):
    def _build_client(self):
        init = MagicMock()
        init.url = 'https://pfsense.test'
        init.api_key = 'test-key'
        init.ssl = False
        init.verifycert = False
        init.default_interface = 'wan'
        init.params = {'pfsense': {'default_interface': 'wan'}}
        client = PfsenseFunction(init)
        client._initialize_api_session()
        return client

    @responses.activate
    def test_add_firewall_rule_posts_and_applies(self):
        client = self._build_client()
        rule_url = 'https://pfsense.test/api/v1/firewall/rule'
        apply_url = 'https://pfsense.test/api/v1/firewall/apply'
        list_url = 'https://pfsense.test/api/v1/firewall/rule'

        responses.add(
            responses.POST,
            rule_url,
            json={'status': 'ok', 'code': 200, 'return_code': 0, 'message': 'ok', 'data': {}},
            status=200,
        )
        responses.add(
            responses.POST,
            apply_url,
            json={'status': 'ok', 'code': 200, 'return_code': 0, 'message': 'ok', 'data': {'applied': True}},
            status=200,
        )
        responses.add(
            responses.GET,
            list_url,
            json={'status': 'ok', 'code': 200, 'return_code': 0, 'message': 'ok', 'data': []},
            status=200,
        )

        result = client.add_firewall_rule(src=['203.0.113.50'])
        self.assertIsInstance(result, dict)
        post_calls = [c for c in responses.calls if c.request.method == 'POST']
        self.assertEqual(len(post_calls), 2)
        posted = json.loads(post_calls[0].request.body)
        self.assertIn('type', posted)


if __name__ == '__main__':
    unittest.main()
