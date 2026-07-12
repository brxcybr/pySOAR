#!/usr/bin/env python3

import os
import unittest
from unittest.mock import MagicMock

from integrations.misp_functions import MispFunction


class TestMispMockMode(unittest.TestCase):
    def test_placeholder_config_enables_mock_mode(self):
        init = MagicMock()
        init.url = 'https://{MISP_URL}'
        init.api_key = '{API_KEY}'
        init.ssl = False
        init.verifycert = False
        misp = MispFunction(init)
        self.assertTrue(misp._mock)
        values = misp.get_misp_event_by_type('ip-dst')
        self.assertEqual(len(values), 3)

    def test_env_var_enables_mock_mode(self):
        os.environ['PYSOAR_MOCK_INTEGRATIONS'] = '1'
        try:
            init = MagicMock()
            init.url = 'https://misp.local'
            init.api_key = 'secret'
            init.ssl = False
            init.verifycert = False
            misp = MispFunction(init)
            self.assertTrue(misp._mock)
            self.assertTrue(misp.enable_threat_feed())
        finally:
            os.environ.pop('PYSOAR_MOCK_INTEGRATIONS', None)


if __name__ == '__main__':
    unittest.main()
