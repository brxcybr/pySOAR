#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock, patch

from classes import PlaybookManager, PlaybookFunction, ConfigurationManager


def _child_logic():
    return [
        PlaybookFunction(
            name="add_firewall_rule",
            trigger={"type": "always"},
            on_success="halt_playbook",
            on_fail="halt_playbook",
        ),
        PlaybookFunction(name="halt_playbook", trigger={"type": "always"}),
    ]


def _parent_logic(child="child"):
    return [
        PlaybookFunction(
            name="get_misp_event_by_type",
            trigger={"type": "always"},
            on_success=f"run_playbook:{child}",
            on_fail="halt_playbook",
        ),
        PlaybookFunction(
            name=f"run_playbook:{child}",
            trigger={"type": "always"},
            on_success="halt_playbook",
            on_fail="halt_playbook",
        ),
        PlaybookFunction(name="halt_playbook", trigger={"type": "always"}),
    ]


class TestPlaybookComposition(unittest.TestCase):
    def _make_manager(self):
        mgr = PlaybookManager()
        mgr.playbooks_data["parent"] = {
            "enabled": True,
            "integration_dependencies": ["misp"],
            "logic": [f.to_dict() for f in _parent_logic()],
        }
        mgr.playbooks_data["child"] = {
            "enabled": True,
            "integration_dependencies": ["pfsense"],
            "logic": [f.to_dict() for f in _child_logic()],
        }
        return mgr

    @patch.object(ConfigurationManager, "resolve_callable")
    @patch("classes.find_integration_for_function")
    def test_parent_runs_child_and_merges_shared_data(self, mock_find, mock_resolve):
        producer_integration = MagicMock()
        producer_integration.returns = ["ip-dst"]
        responder_integration = MagicMock()
        responder_integration.returns = ["ip-dst", "pfsense-firewall-status"]
        mock_find.side_effect = lambda _cm, name: (
            producer_integration if name == "get_misp_event_by_type" else responder_integration
        )

        calls = []

        def side_effect(function_name):
            if function_name == "get_misp_event_by_type":
                return_value = ["203.0.113.5"]
            else:
                return_value = True

            def method(**_kwargs):
                calls.append(function_name)
                return return_value

            return MagicMock(), method

        mock_resolve.side_effect = side_effect

        mgr = self._make_manager()
        config_mgr = ConfigurationManager()
        config_mgr._playbook_mgr = mgr

        shared = mgr.launch_playbook(
            "parent", config_mgr, once=True, skip_validation=True, return_shared_data=True
        )
        self.assertIn("get_misp_event_by_type", calls)
        self.assertIn("add_firewall_rule", calls)
        self.assertIsInstance(shared, dict)
        ip_dst = shared.get("ip-dst")
        if isinstance(ip_dst, list):
            self.assertIn("203.0.113.5", ip_dst)
        else:
            self.assertEqual(ip_dst, "203.0.113.5")
        values = [o["value"] for o in shared.get("observables", [])]
        self.assertIn("203.0.113.5", values)

    @patch.object(ConfigurationManager, "resolve_callable")
    @patch("classes.find_integration_for_function")
    def test_recursion_is_blocked(self, mock_find, mock_resolve):
        integration = MagicMock()
        integration.returns = []
        mock_find.return_value = integration
        method = MagicMock(return_value=True)
        mock_resolve.return_value = (MagicMock(), method)

        mgr = PlaybookManager()
        mgr.playbooks_data["loop"] = {
            "enabled": True,
            "integration_dependencies": [],
            "logic": [
                f.to_dict()
                for f in [
                    PlaybookFunction(
                        name="run_playbook:loop",
                        trigger={"type": "always"},
                        on_success="halt_playbook",
                        on_fail="halt_playbook",
                    ),
                    PlaybookFunction(name="halt_playbook", trigger={"type": "always"}),
                ]
            ],
        }
        config_mgr = ConfigurationManager()
        config_mgr._playbook_mgr = mgr

        # The child launch fails (recursive), step routes to on_fail -> halt.
        result = mgr.launch_playbook("loop", config_mgr, once=True, skip_validation=True)
        self.assertTrue(result)

    def test_validator_flags_bad_composition(self):
        from playbook_validator import validate_playbook

        playbook = MagicMock()
        playbook.name = "parent"
        playbook.integration_deps = []
        playbook.logic = [
            PlaybookFunction(
                name="run_playbook:parent",
                trigger={"type": "always"},
                on_success="halt_playbook",
                on_fail="halt_playbook",
            ),
            PlaybookFunction(name="halt_playbook", trigger={"type": "always"}),
        ]
        result = validate_playbook(playbook, None)
        codes = [issue.code for issue in result.errors]
        self.assertIn("recursive_playbook", codes)

    def test_validator_flags_missing_child(self):
        from playbook_validator import validate_playbook

        mgr = PlaybookManager()
        mgr.playbooks_data["parent"] = {"enabled": True}
        config_mgr = MagicMock()
        config_mgr.playbook_mgr = mgr
        config_mgr.enabled_playbook_functions = {}
        config_mgr.enabled_integrations = []

        playbook = MagicMock()
        playbook.name = "parent"
        playbook.integration_deps = []
        playbook.logic = [
            PlaybookFunction(
                name="run_playbook:ghost",
                trigger={"type": "always"},
                on_success="halt_playbook",
                on_fail="halt_playbook",
            ),
            PlaybookFunction(name="halt_playbook", trigger={"type": "always"}),
        ]
        result = validate_playbook(playbook, config_mgr)
        codes = [issue.code for issue in result.errors]
        self.assertIn("unknown_child_playbook", codes)


class TestIdempotency(unittest.TestCase):
    @patch.object(ConfigurationManager, "resolve_callable")
    @patch("classes.find_integration_for_function")
    def test_idempotent_action_skipped_second_time(self, mock_find, mock_resolve):
        import os
        import tempfile
        from unittest.mock import patch as env_patch

        from core.state_store import StateStore

        integration = MagicMock()
        integration.returns = []
        mock_find.return_value = integration
        method = MagicMock(return_value=True)
        mock_resolve.return_value = (MagicMock(), method)

        tmp = tempfile.mkdtemp(prefix="pysoar-idem-")
        with env_patch.dict(os.environ, {"PYSOAR_STATE_DB": os.path.join(tmp, "s.db")}):
            StateStore.reset()
            step = PlaybookFunction(
                name="add_firewall_rule",  # manifest declares idempotent: true
                trigger={"type": "always"},
                on_success="halt_playbook",
                on_fail="halt_playbook",
            )
            config_mgr = ConfigurationManager()
            shared = {"ip-dst": "203.0.113.77"}

            step.execute(dict(shared), config_mgr)
            self.assertEqual(method.call_count, 1)
            step.execute(dict(shared), config_mgr)
            # Second identical invocation inside the dedupe window is skipped.
            self.assertEqual(method.call_count, 1)

            # Different args execute normally.
            step.execute({"ip-dst": "203.0.113.88"}, config_mgr)
            self.assertEqual(method.call_count, 2)
        StateStore.reset()


if __name__ == "__main__":
    unittest.main()
