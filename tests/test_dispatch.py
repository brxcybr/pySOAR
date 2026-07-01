#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock, patch

from integrations.dispatch import (
    build_kwargs,
    merge_result,
    resolve_method_name,
    is_success,
)
from classes import PlaybookFunction, ConfigurationManager


class TestDispatchHelpers(unittest.TestCase):
    def test_resolve_method_name_alias(self):
        self.assertEqual(
            resolve_method_name("get_misp_event_by_type"),
            "get_event_data_by_type",
        )

    def test_build_kwargs_misp_fetch(self):
        method = MagicMock()
        kwargs = build_kwargs(
            "get_misp_event_by_type",
            method,
            {},
            ["ip-dst"],
        )
        self.assertEqual(kwargs, {"data_type": "ip-dst"})

    def test_build_kwargs_firewall_block(self):
        method = MagicMock()
        kwargs = build_kwargs(
            "add_firewall_rule",
            method,
            {"ip-dst": ["203.0.113.1"]},
            None,
        )
        self.assertEqual(kwargs, {"src": ["203.0.113.1"]})

    def test_merge_result_ip_list(self):
        shared = {}
        shared = merge_result(shared, "get_misp_event_by_type", ["203.0.113.1"])
        self.assertEqual(shared["ip-dst"], ["203.0.113.1"])

    def test_is_success(self):
        self.assertFalse(is_success(None))
        self.assertFalse(is_success(False))
        self.assertTrue(is_success(["1.2.3.4"]))


class TestPlaybookFunctionExecute(unittest.TestCase):
    @patch.object(ConfigurationManager, "resolve_callable")
    @patch("classes.find_integration_for_function")
    def test_execute_returns_shared_data_first(self, mock_find, mock_resolve):
        integration = MagicMock()
        integration.returns = ["ip-dst"]
        mock_find.return_value = integration

        method = MagicMock(return_value=["10.0.0.1"])
        mock_resolve.return_value = (MagicMock(), method)

        func = PlaybookFunction(
            name="get_misp_event_by_type",
            trigger={"type": "always"},
            on_success="add_firewall_rule",
            on_fail="halt_playbook",
            data_dependencies=["ip-dst"],
        )
        config_mgr = MagicMock()
        config_mgr.resolve_callable.return_value = (MagicMock(), method)
        shared, nxt = func.execute({}, config_mgr)
        self.assertEqual(shared["ip-dst"], ["10.0.0.1"])
        self.assertEqual(nxt, "add_firewall_rule")


if __name__ == "__main__":
    unittest.main()
