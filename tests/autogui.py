#!/usr/bin/env python3

import subprocess
import pyautogui
import os
from classes import Playbook
import time


def create_playbook(new_playbook_name='practicum', interval=2):
    # Start the application in a subprocess
    app_process = subprocess.Popen(['python', 'pysoar.py'], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE,
                                        stdin=subprocess.PIPE)
    stdout, stderr = app_process.communicate()
    time.sleep(5)  # Wait for the app to start

    print(f"STDOUT:\n\t {stdout}")
    print(f"STDERR:\n\n\t {stderr}")
    # Simulate keystrokes for creating a new playbook
    # Replace these with the actual keystrokes for your application
    pyautogui.press(['down', 'enter'], interval=interval) # Select CREATE PLAYBOOK
    pyautogui.write(new_playbook_name, interval=0.2) # Name playbook
    pyautogui.press(['enter','down','enter'], interval=interval) # Add function
    pyautogui.press(['down', 'down', 'down', 'down', 'enter'], interval=interval) # Add enable_threat_feed function
    pyautogui.press(['enter'], interval=interval) # Select data_dependencies "NONE"
    pyautogui.press(['enter'], interval=interval) # Select trigger of "Continuous"
    pyautogui.press(['enter'], interval=interval) # What should happen if this action fails? "halt_playbook"
    pyautogui.press(['down', 'enter'], interval=interval)  # What should happen if this action succeeds? "execute next action"
    pyautogui.press(['down', 'down', 'enter'], interval=interval) # Add section function "get_misp_event_by_type"
    pyautogui.press(['down', 'enter'], interval=interval) # Select data_dependency "ip-dst"
    pyautogui.press(['down', 'enter'], interval=interval) # Select trigger "time interval"
    pyautogui.press(['enter'], interval=interval) # Keep default of 60 seconds
    pyautogui.press(['enter'], interval=interval) # What should happen if this action fails? "halt_playbook"
    pyautogui.press(['down', 'enter'], interval=interval)  # What should happen if this action succeeds? "execute next action"
    pyautogui.press(['down', 'down', 'down', 'down', 'down', 'down', 'enter'], interval=interval) # Add section function "add_firewall_rule"
    pyautogui.press(['enter'], interval=interval) # Select data_dependencies "NONE"
    pyautogui.press(['enter'], interval=interval) # Select trigger of "Continuous"
    pyautogui.press(['enter'], interval=interval) # What should happen if this action fails? "halt_playbook"
    pyautogui.press(['down', 'down', 'enter'], interval=interval) # What should happen if this action succeeds? "loop to previous action"
    pyautogui.press(['down', 'enter'], interval=interval) # Select "get_misp_event_by_type"
    pyautogui.press(['enter', 'enter'], interval=interval)  # Is this correct? "yes", Save playbook to disk? "yes"

    # Menu cycle should be complete
    print(f"STDOUT:\n\t {stdout}")
    print(f"STDERR:\n\n\t {stderr}")
    pyautogui.press(['down', 'down', 'down', 'down', 'down','down', 'enter'], interval=interval) # Exit

    app_process.terminate() # Terminate the application
    
def compare_playbooks(playbook_name='test', new_playbook_name='practicum'):
    playbook_filepath = Path(f"./playbooks/{playbook_name}.yaml")
    new_playbook_filepath = Path(f"./playbooks/{new_playbook_name}.yaml")
    # Load the original and new playbooks
    original_playbook = Playbook(playbook_name)
    original_playbook.load()
    new_playbook = Playbook(new_playbook_name)
    new_playbook.load()
    
    # Compare the enabled field
    # Compare the playbooks
    assert original_playbook.enabled == new_playbook.enabled
    assert sorted(original_playbook.integration_deps) == sorted(new_playbook.integration_deps)
    
    original_logic = [func.to_dict() for func in original_playbook.logic]
    new_logic = [func.to_dict() for func in new_playbook.logic]
    assert original_logic == new_logic

    for i in range(len(original_playbook.functions)):
        assert original_playbook.logic[i].name == new_playbook.logic[i].name
        assert original_playbook.logic[i].trigger == new_playbook.logic[i].trigger
        assert original_playbook.logic[i].on_success == new_playbook.logic[i].on_success
        assert original_playbook.logic[i].on_fail == new_playbook.logic[i].on_fail
        assert original_playbook.logic[i].data_dependencies == new_playbook.logic[i].data_dependencies

    # Clean up: Remove the created playbook file if it exists
    if new_playbook_filepath.exists():
        new_playbook_filepath.unlink()

if __name__ == '__main__':
    create_playbook()