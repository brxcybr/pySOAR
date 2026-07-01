#!/usr/bin/env python3

import unittest
from unittest.mock import patch, MagicMock
from classes import ConfigurationManager


class TestConfigurationManager(unittest.TestCase):

    def setUp(self):
        self.mock_log = MagicMock()
        patcher1 = patch('classes.Log.get_instance', return_value=self.mock_log)
        patcher2 = patch('classes.Integration')
        patcher3 = patch('classes.PlaybookManager')
        patcher4 = patch('classes.os.listdir', return_value=[])

        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        self.addCleanup(patcher4.stop)

        patcher1.start()
        self.mock_integration = patcher2.start()
        patcher3.start()
        patcher4.start()

        self.config_manager = ConfigurationManager()
        self.config_manager.misp = MagicMock()
        self.config_manager._enabled_feeds = {}
        self.config_manager._enabled_playbook_functions = {}

    def test_get_enabled_integrations_no_files(self):
        self.config_manager._enabled_integrations = []
        self.assertEqual(self.config_manager.enabled_integrations, [])

    def test_add_integration_already_enabled(self):
        self.config_manager.integration_mgr.add_integration = MagicMock(
            return_value=("test_integration is already enabled. Returning...", [])
        )
        self.config_manager._add_integration('test_integration')
        self.mock_log.warning.assert_called_with(
            'test_integration is already enabled. Returning...'
        )

    def test_remove_integration_no_matching_playbooks(self):
        self.config_manager._enabled_playbooks = {}
        self.config_manager.integration_mgr.remove_integration = MagicMock()
        self.config_manager._remove_integration('test_integration')
        self.config_manager.integration_mgr.remove_integration.assert_not_called()


if __name__ == '__main__':
    unittest.main()
