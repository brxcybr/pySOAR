import unittest
import subprocess
import time
from pathlib import Path

try:
    import pyautogui
except ImportError:
    pyautogui = None

import pytest
from classes import Playbook

pytestmark = pytest.mark.skipif(pyautogui is None, reason="PyAutoGUI not installed")

class TestPlaybookCreationGUI(unittest.TestCase):

    def setUp(self):
        self.playbook_name = "test"
        self.new_playbook_name = "practicum"
        self.playbook_filepath = Path(f"./playbooks/{self.playbook_name}.yaml")
        self.new_playbook_filepath = Path(f"./playbooks/{self.new_playbook_name}.yaml")
        # Start the application in a subprocess
        self.app_process = subprocess.Popen(['python', 'pysoar.py'], 
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE,
                                            stdin=subprocess.PIPE)
        stdout, stderr = self.app_process.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        time.sleep(5)  # Wait for the app to start

    def test_create_playbook(self):
        # Simulate keystrokes for creating a new playbook
        # Replace these with the actual keystrokes for your application
        pyautogui.press('down')    # Navigate down
        time.sleep(0.5)
        pyautogui.press('enter')   # Select CREATE PLAYBOOK
        time.sleep(0.5)
        pyautogui.typewrite(self.new_playbook_name) # Name playbook 
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('down') # Add function 
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('down') # Add enable_threat_feed function
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('enter') # Select data_dependencies "NONE"
        time.sleep(0.5)
        pyautogui.press('enter') # Select trigger of "Continuous"
        time.sleep(0.5)
        pyautogui.press('enter') # What should happen if this action fails? "halt_playbook"
        time.sleep(0.5)
        pyautogui.press('down')  # What should happen if this action succeeds? "execute next action"
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('down') # Add section function "get_misp_event_by_type"
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('down') # Select data_dependency "ip-dst"
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('down') # Select trigger "time interval"
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('enter') # Keep default of 60 seconds 
        time.sleep(0.5)
        pyautogui.press('enter') # What should happen if this action fails? "halt_playbook"
        time.sleep(0.5)
        pyautogui.press('down')  # What should happen if this action succeeds? "execute next action"
        time.sleep(0.5)
        pyautogui.press('enter') 
        time.sleep(0.5)
        pyautogui.press('down')  # Add add_firewall_rule function
        time.sleep(0.5)
        pyautogui.press('down') 
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('enter') 
        time.sleep(0.5)
        pyautogui.press('enter') # Select trigger of "Continuous"
        time.sleep(0.5)
        pyautogui.press('enter') # What should happen if this action fails? "halt_playbook"
        time.sleep(0.5)
        pyautogui.press('down') # What should happen if this action succeeds? "loop to previous action"
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('enter') 
        time.sleep(0.5)
        pyautogui.press('down') # Select "get_misp_event_by_type"
        time.sleep(0.5)
        pyautogui.press('enter') 
        time.sleep(0.5)
        pyautogui.press('enter') # Is this correct? "yes"
        time.sleep(0.5)
        pyautogui.press('enter') # Save playbook to disk? "yes"
        time.sleep(0.5)
        # Menu cycle should be complete
        # Return to main menu 
        pyautogui.press('down') 
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('enter') # Back to main menu 
        time.sleep(0.5)
        # Exit 
        pyautogui.press('down') 
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('down')
        time.sleep(0.5)
        pyautogui.press('enter') # Exit
        time.sleep(0.5)
        
    def test_compare_playbooks(self):
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
        # Terminate the application subprocess
        self.app_process.terminate()
        # Clean up: Remove the created playbook file if it exists
        pass
        #if self.new_playbook_filepath.exists():
        #    self.new_playbook_filepath.unlink()

if __name__ == '__main__':
    unittest.main()
