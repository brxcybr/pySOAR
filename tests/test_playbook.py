#!/usr/bin/env python3

import unittest
import os
from classes import Playbook, PlaybookFunction, ConfigurationManager

class TestPlaybookCreation(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPlaybookCreation, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def setUp(self):
        # Set up the initial conditions for your test
        self.playbook_name = "test"
        self.new_playbook_name = "practicum"
        self.playbook_filepath = f"./playbooks/{self.playbook_name}.yaml"
        self.new_playbook_filepath = f"./playbooks/{self.new_playbook_name}.yaml"
        self.config_mgr = ConfigurationManager()
        self.playbook_mgr = self.config_mgr.playbook_mgr
    
    def check_data(self, playbook):
        # Print the in-memory contents of the new playbook
        print(f"playbook.name: {playbook.name}")
        print(f"playbook.filename: {playbook.filename}")
        print(f"playbook.path: {playbook.path}")
        print(f"playbook.integration_deps: {playbook.integration_deps}")
        print(f"playbook.logic: {playbook.logic}")
        print(f"playbook.functions: {playbook.functions}")
        print(f"playbook.data: {playbook.data}")
        print(f"playbook.enabled: {playbook.enabled}")
        print(f"playbook.exists: {playbook.exists}")
        print(f"playbook.is_running: {playbook.is_running}")

    def test_create_and_compare_playbook(self, debug=False):
        # Step 1: Create a playbook in memory
        playbook = Playbook(self.new_playbook_name)
        func1 = PlaybookFunction(
            name="enable_threat_feed",
            trigger={"type": "always"},
            on_success="get_misp_event_by_type",
            on_fail="halt_playbook",
                )
        func2 = PlaybookFunction(
                    name="get_misp_event_by_type",
                    trigger={
                        "type": "time",
                        "duration": 60,
                                },
                    on_success="add_firewall_rule",
                    on_fail="halt_playbook",
                    data_dependencies=['ip-dst'],
                )
        func3 = PlaybookFunction(
                    name="add_firewall_rule",
                    trigger={"type": "always"},
                    on_success="get_misp_event_by_type",
                    on_fail="halt_playbook",
                )
        func4 = PlaybookFunction(
                    name="halt_playbook",
                    trigger={"type": "always"},
                )
        # Append functions to playbook logic
        playbook.add_playbook_function(func1)
        playbook.add_playbook_function(func2)
        playbook.add_playbook_function(func3)
        playbook.add_playbook_function(func4)
        playbook.integration_deps = ['misp', 'pfsense']
        playbook.enabled = True
        
        if debug: # Check the state of the data before updating
            print("\nBefore updating:")
            self.check_data(playbook)
        playbook.update() # Update the playbook
        
        if debug: # Verify the state of the data after updating
            print("\nAfter updating:")
            self.check_data(playbook)
        
        self.playbook_mgr.update_playbook_data(playbook.name, playbook.data)

        if debug: # Verify the state of the data after updating
            print("\nAfter updating playbook data:")
            print(self.playbook_mgr.playbooks_data[playbook.name])
            
        self.playbook_mgr.save_playbook(playbook.name)

        # Step 3: Load the original and new playbooks
        original_playbook = Playbook(self.playbook_name)
        original_playbook.load()
        new_playbook = Playbook(self.new_playbook_name)
        new_playbook.load()

        # Compare the enabled field 
        self.assertEqual(original_playbook.enabled, new_playbook.enabled)
        # Compare integration dependencies
        self.assertEqual(original_playbook.integration_deps.sort(), new_playbook.integration_deps.sort())
        # Compare the logic (convert both playbooks to list of dictionaries)
        original_logic = [func.to_dict() for func in original_playbook.logic]
        new_logic = [func.to_dict() for func in new_playbook.logic]
        self.assertEqual(original_logic, new_logic)
        # Compare each function 
        for i in range(len(original_playbook.functions)):
            self.assertEqual(original_playbook.logic[i].name, new_playbook.logic[i].name)
            self.assertEqual(original_playbook.logic[i].trigger, new_playbook.logic[i].trigger)
            if original_playbook.logic[i].on_success:
                self.assertEqual(original_playbook.logic[i].on_success, new_playbook.logic[i].on_success)
            if original_playbook.logic[i].on_fail:
                self.assertEqual(original_playbook.logic[i].on_fail, new_playbook.logic[i].on_fail)
            if original_playbook.logic[i].data_dependencies:
                self.assertEqual(original_playbook.logic[i].data_dependencies, new_playbook.logic[i].data_dependencies)
        
    def tearDown(self):
        # Clean up: Remove the created playbook file if it exists
        if os.path.exists(self.new_playbook_filepath):
            os.remove(self.new_playbook_filepath)

if __name__ == '__main__':
    unittest.main()
