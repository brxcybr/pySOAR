#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock, patch

from classes import PlaybookManager, PlaybookFunction, ConfigurationManager


class TestPlaybookExecution(unittest.TestCase):
    def _sample_logic(self):
        return [
            PlaybookFunction(
                name="enable_threat_feed",
                trigger={"type": "always"},
                on_success="get_misp_event_by_type",
                on_fail="halt_playbook",
            ),
            PlaybookFunction(
                name="get_misp_event_by_type",
                trigger={"type": "always"},
                on_success="add_firewall_rule",
                on_fail="halt_playbook",
                data_dependencies=["ip-dst"],
            ),
            PlaybookFunction(
                name="add_firewall_rule",
                trigger={"type": "always"},
                on_success="halt_playbook",
                on_fail="halt_playbook",
            ),
            PlaybookFunction(name="halt_playbook", trigger={"type": "always"}),
        ]

    @patch.object(ConfigurationManager, "resolve_callable")
    @patch("classes.find_integration_for_function")
    def test_launch_playbook_once(self, mock_find, mock_resolve):
        integration = MagicMock()
        integration.returns = ["ip-dst"]
        mock_find.return_value = integration

        def side_effect(_self, function_name):
            method = MagicMock()
            if function_name == "enable_threat_feed":
                method.return_value = True
            elif function_name == "get_misp_event_by_type":
                method.return_value = ["203.0.113.5"]
            elif function_name == "add_firewall_rule":
                method.return_value = True
            return MagicMock(), method

        mock_resolve.side_effect = side_effect

        mgr = PlaybookManager()
        mgr.playbooks_data["test"] = {
            "enabled": True,
            "integration_dependencies": ["misp", "pfsense"],
            "logic": [f.to_dict() for f in self._sample_logic()],
        }

        config_mgr = ConfigurationManager()
        result = mgr.launch_playbook("test", config_mgr, once=True, skip_validation=True)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
