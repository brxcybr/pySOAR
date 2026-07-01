#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock

from classes import Playbook, PlaybookFunction
from playbook_validator import validate_playbook


class TestPlaybookValidator(unittest.TestCase):
    def _build_playbook(self):
        playbook = Playbook('sample')
        playbook.logic = [
            PlaybookFunction(
                name='enable_threat_feed',
                trigger={'type': 'always'},
                on_success='get_misp_event_by_type',
                on_fail='halt_playbook',
            ),
            PlaybookFunction(
                name='get_misp_event_by_type',
                trigger={'type': 'time', 'duration': 60},
                on_success='add_firewall_rule',
                on_fail='halt_playbook',
                data_dependencies=['ip-dst'],
            ),
            PlaybookFunction(
                name='add_firewall_rule',
                trigger={'type': 'always'},
                on_success='halt_playbook',
                on_fail='halt_playbook',
            ),
            PlaybookFunction(name='halt_playbook', trigger={'type': 'always'}),
        ]
        playbook.integration_deps = ['misp', 'pfsense']
        return playbook

    def test_valid_playbook_passes(self):
        config_mgr = MagicMock()
        config_mgr.enabled_playbook_functions = {
            'enable_threat_feed': True,
            'get_misp_event_by_type': True,
            'add_firewall_rule': True,
        }
        integration = MagicMock()
        integration.name = 'misp'
        integration.playbook_functions = ['enable_threat_feed', 'get_misp_event_by_type']
        integration2 = MagicMock()
        integration2.name = 'pfsense'
        integration2.playbook_functions = ['add_firewall_rule']
        config_mgr.enabled_integrations = [integration, integration2]

        result = validate_playbook(self._build_playbook(), config_mgr)
        self.assertTrue(result.is_valid)

    def test_dangling_branch_fails(self):
        playbook = self._build_playbook()
        playbook.logic[0].on_success = 'missing_step'
        result = validate_playbook(playbook)
        self.assertFalse(result.is_valid)


if __name__ == '__main__':
    unittest.main()
