#!/usr/bin/env python3

import unittest

from triggers import evaluate_condition, wait_for_trigger
from classes import PlaybookFunction


class TestTriggers(unittest.TestCase):
    def test_shared_data_present(self):
        condition = {'type': 'shared_data_present', 'key': 'ip-dst'}
        self.assertFalse(evaluate_condition(condition, {}))
        self.assertTrue(evaluate_condition(condition, {'ip-dst': ['1.2.3.4']}))

    def test_condition_skip_mode(self):
        func = PlaybookFunction(
            name='add_firewall_rule',
            trigger={
                'type': 'condition',
                'condition': {
                    'type': 'shared_data_present',
                    'key': 'ip-dst',
                    'mode': 'skip',
                },
            },
        )
        self.assertFalse(wait_for_trigger(func, shared_data={}))


if __name__ == '__main__':
    unittest.main()
