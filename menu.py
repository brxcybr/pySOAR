from classes import ConfigurationManager, Integration, Log, Playbook, PlaybookFunction
import curses
import traceback

class Menu:
    """This class is used to manage the menu system."""

    def __init__(self):
        self.current_menu = self.main_menu
        self.menu_stack = []
        self._config_mgr = ConfigurationManager()
        self._playbook_mgr = self._config_mgr.playbook_mgr
        self.current_option = 0 # The currently selected menu option
        self.current_header = self.welcome_header
        self.current_playbook = None
        self.current_function = None
        self.current_integration = None
        self.current_success_or_fail = None
        self.temp = None # Used for add temporary values
        self.log = Log().get_instance()

    # Main Functions
    def draw_menu(self, options):
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.clear()

        self.log.debug(f"Drawing menu with options: {options}.")
        if max_y < 20:  # if the window is too short for the full header, show a compact version
            header = f"{self.top_header}\n"
        else:
            header = self.current_header
        try:
            header_lines = header.count('\n')
            self.stdscr.addstr(header + '\n\n')

            for idx, option in enumerate(options):
                numbered_option = f"{idx + 1}. {option.upper()}"  # Add numbering to the option
                if idx + header_lines < max_y - 1:  # Check if there's space to print the option
                    if idx == self.current_option:
                        self.stdscr.addstr(f">>> {numbered_option}\n", curses.A_REVERSE)
                    else:
                        self.stdscr.addstr(f"    {numbered_option}\n")
                else:
                    # Not enough space to print more options
                    break
        except curses.error as e:
                self.stdscr.addstr(0, 0, "Screen too small for menu.")
            
        self.log.debug(f"Current option: {self.current_option}")
        self.stdscr.refresh()

    def draw_input_prompt(self, prompt):
        # Get the height and width of the screen
        height, width = self.stdscr.getmaxyx()

        # Clear the screen
        self.stdscr.clear()

        # Add the header if it exists
        if self.current_header:
            try:
                # Split the header into lines and print each line
                header_lines = self.current_header.split('\n')
                for i, line in enumerate(header_lines):
                    self.stdscr.addstr(i, 0, line)
            except curses.error as e:
                # Handle any curses error that might occur
                self.stdscr.addstr(0, 0, "Screen too small for header.")

        # Calculate the y position for the input prompt (one line below the header)
        prompt_y = len(self.current_header.split('\n'))

        # Add the prompt on the same line
        try:
            self.stdscr.addstr(prompt_y, 0, prompt)
        except curses.error as e:
            # Handle any curses error that might occur
            self.stdscr.addstr(prompt_y, 0, "Screen too small for prompt.")

        # Get user input starting right after the prompt
        input_x = len(prompt)  # Start input right after the prompt
        curses.echo()
        name = self.stdscr.getstr(prompt_y, input_x, width - input_x).decode('utf-8')
        curses.noecho()

        # Refresh the screen to update the changes
        self.stdscr.refresh()

        # Debug
        self.log.debug(f"User provided input: {name}")
        return name

    def run(self, stdscr):
        self.stdscr = stdscr
        self.display_menu()
        
    def display_menu(self):
        """Display the menu"""
        while True:
            if callable(self.current_menu):
                self.current_menu()
            if not self.menu_stack:
                break
            self.current_menu = self.menu_stack.pop()
            self.stdscr.refresh()

    def main_menu(self):
        """Main menu implementation"""  
        # Turn off cursor blinking
        curses.curs_set(0)
                                                        
        # Set menu options
        options = [
            "VISUALIZE PLAYBOOK",
            "CREATE PLAYBOOK",
            "EDIT PLAYBOOK",
            "LAUNCH PLAYBOOK",
            "STOP PLAYBOOK",
            "REMOVE PLAYBOOK",
            "CONFIGURE",
            "EXIT"
        ]
        self.current_option = 0 # Initialize menu items and start loop
        self.draw_menu(options)
        self.menu_stack.append(self.current_menu) # Add current menu to the stack before changing
        while True:
            key = self.stdscr.getch()
            if key == curses.KEY_UP:
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                self.current_option = (self.current_option + 1) % len(options)
            elif key == curses.KEY_ENTER or key in [10, 13]:
                selected_option = self.current_option  # +1 because options start from 1 not 0
                # Logic to handle each option
                if selected_option == 0: # Visualize Playbook
                    self.current_header = self.top_header
                    self.current_menu = self.view_playbook_menu
                    self.view_playbook_menu()
                elif selected_option == 1: # Create Playbook
                    self.current_menu = self.playbook_editor_menu
                    self.playbook_editor_menu(new=True)
                elif selected_option == 2: # Edit Playbook
                    if len(self.playbook_mgr.playbook_names) == 0:
                        self.current_header += '\n\nNO PLAYBOOKS TO EDIT'
                        continue
                    self.current_menu = self.playbook_editor_menu
                    self.playbook_editor_menu(new=False)
                elif selected_option == 3: # Launch Playbook
                    if len(self.playbook_mgr.playbook_names) == 0:
                        self.current_header += '\n\nNO PLAYBOOKS TO LAUNCH'
                        continue
                    self.current_header = self.top_header
                    self.current_menu = self.launch_playbook_menu # Add current menu to the stack before changing
                    self.launch_playbook_menu()
                elif selected_option == 4: # Stop Playbook
                    if len(self.playbook_mgr.playbook_names) == 0:
                        self.current_header += '\n\nNO PLAYBOOKS TO LAUNCH'
                        continue
                    self.current_header = self.top_header
                    self.current_menu = self.stop_playbook_menu # Add current menu to the stack before changing
                    self.stop_playbook_menu()
                elif selected_option == 5: # Remove Playbook
                    if len(self.playbook_mgr.playbook_names) == 0:
                        self.current_header += '\n\nNO PLAYBOOKS TO LAUNCH'
                        continue
                    self.current_header = self.top_header
                    self.current_menu = self.remove_playbook_menu # Add current menu to the stack before changing
                    self.remove_playbook_menu()
                elif selected_option == 6:  # Configure
                    self.current_header = self.config_header
                    self.current_menu = self.configuration_menu # Add current menu to the stack before changing
                    self.configuration_menu()
                elif selected_option == 7: # Exit
                    # Turn cursor blinking back on before exiting the menu
                    curses.curs_set(1)
                    exit(0)
            self.current_header = self.welcome_header # Reset the header
            self.draw_menu(options)
    
    def clear_and_refresh(self):
        """Clear and refresh the screen"""
        self.stdscr.clear()
        self.stdscr.refresh()

    # Playbook Visualization
    def view_playbook_menu(self):
        """Top menu for Playbook Editor"""
        # Call the playbook selection menu
        if len(self.playbook_mgr.playbook_names) == 0:
            self.log.debug(f"No playbooks to display.")
            return
        elif len(self.non_template_playbooks) == 1:
            self.current_playbook = self.non_template_playbooks[0]
        else:
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.select_playbook_menu
            self.select_playbook_menu()
        
        # User chose to go back or an error occurred
        if not self.current_playbook:
            self.log.debug(f"User chose to go back or an error occurred.")
            self.log.error(f"Error viewing playbook: No playbook selected.")
            self.current_menu = self.menu_stack[-1]
            return
        try: 
            self.current_header += '\nPLAYBOOK>>> (VISUALIZE)'
            self.current_playbook.visualize() # Call the visualize method on the playbook
        except Exception as e:
            self.current_header += '\nPLAYBOOK>>> (VISUALIZE) (ERROR)'
            self.log.error(f"Error visualizing playbook: {e}")
        
        self.current_menu = self.menu_stack.pop() # Return to previous menu
        return # Return to menu
   
    # Playbook Editor        
    def playbook_editor_menu(self, new=False):
        """Top menu for Playbook Editor"""
        self.build_header()
        self.clear_and_refresh() # Clear and refresh the screen
        # Determine value of variable "new", and send them to that menu before returning to main configuration menu
        if new:
            self.log.debug(f"Sending user to the name playbook menu.")
            self.current_playbook = self.draw_input_prompt("NAME YOUR PLAYBOOK>>>  ")
        else:
            self.log.debug(f"Sending user to the select playbook menu.")
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.select_playbook_menu
        # User chose to go back or an error occurred
        if not self.current_playbook:
            self.log.debug(f"User chose to go back or an error occurred.")
            self.log.error(f"Error editing playbook: No playbook selected.")
            self.current_menu = self.menu_stack[-1]
            return 
        
        self.current_playbook = Playbook(self.current_playbook) # Initialize PlaybookObject
        self.build_header() # update the header
        self.clear_and_refresh() # Clear and refresh the screen
        # redraw the menu
        self.stdscr.addstr(0, 0, self.current_header)
        
        # Build the main playbook menu 
        options = ['VIEW LOGIC', 'ADD AN ACTION', 'REMOVE AN ACTION', 'MODIFY AN ACTION', 'BACK']
        self.current_option = 0 # Initialize menu items and start loop
        # Initial display of the menu
        self.draw_menu(options)
        while True:
            key = self.stdscr.getch()
            if key == curses.KEY_UP and self.current_option > 0:
                self.current_option -= 1
            elif key == curses.KEY_DOWN and self.current_option < len(options) - 1:
                self.current_option += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if self.current_option == 0: # 1. VIEW LOGIC
                    if self.current_playbook.logic:
                        self.current_playbook.display() # If there is only one playbook, just display it
                    else: 
                        self.current_header += '\n\nNO LOGIC TO DISPLAY'
                        continue
                elif self.current_option == 1:  # 2. ADD AN ACTION
                    self.menu_stack.append(self.current_menu)
                    self.current_menu = self.add_function_menu
                    self.add_function_menu()
                    self.try_to_update_playbook() # Update the playbook data in memory
                    
                elif self.current_option == 2: # 3. REMOVE AN ACTION
                    if len(self.current_playbook.functions) == 0 or self.current_playbook is None:
                        self.current_header += '\n\nNO ACTIONS TO REMOVE'
                        continue
                    self.menu_stack.append(self.current_menu)
                    self.current_menu = self.edit_function_menu
                    self.edit_function_menu(action='remove')
                    self.try_to_update_playbook() # Update the playbook data in memory
                    
                elif self.current_option == 3: # 4. MODIFY AN ACTION
                    if len(self.current_playbook.functions) == 0 or self.current_playbook is None:
                        self.current_header += '\n\nNO ACTIONS TO MODIFY'
                        continue
                    self.menu_stack.append(self.current_menu)
                    self.current_menu = self.edit_function_menu
                    self.edit_function_menu(action='modify')
                    self.try_to_update_playbook() # Update the playbook data in memory

                elif self.current_option == 4: # 5. BACK
                    self.current_playbook = None
                    self.current_menu = self.menu_stack.pop()

            # Update the display after each key press
            self.build_header() # Update the header
            self.draw_menu(options) # Redraw the menu
   
    def build_header(self):
        """Builds the header for the playbook editor menu"""
        try:
            if not self.current_playbook:
                # Get all enabled functions
                functions = self.config_mgr.enabled_playbook_functions
            else:
                functions = self.current_playbook.functions = self.current_playbook.get_unique_functions()
                self.current_playbook.integration_deps = self.config_mgr.get_unique_integration_dependencies_by_function_list(functions)
            self.current_header = self.playbook_header + '\nPLAYBOOK>>> '
            if self.current_playbook == None:
                self.current_header += '(CONFIG)'
            if self.current_playbook:
                self.current_header += self.current_playbook.name.upper()
                self.current_header += f"\n\tTOOLBOX>>> "
                self.current_header += f", ".join(self.config_mgr.enabled_integrations_list)
            if functions:
                self.current_header += f"\n\t\tTOOL>>> {functions[-1].upper()}"
                self.current_header += f"\n\t\t\tBATTLE RHYTHM>>> (CONFIG)"
            if self.current_playbook.logic:
                self.current_header += f"\t\t\t{self.current_playbook.visualize()}\n\n"
            else:
                self.current_header += "\n\n"
        except Exception:
            self.current_header = self.playbook_header + '\nPLAYBOOK>>> (CONFIG)\n\n'
        return
    
    def select_playbook_menu(self):
        # If there's only one playbook, just return that playbook
        if len(self.non_template_playbooks) == 1:
            self.log.debug(f"Only one playbook found: {self.non_template_playbooks[0]}")
            self.current_playbook = self.non_template_playbooks[0]
            if len(self.menu_stack) > 1:
                self.current_menu = self.menu_stack.pop()
            return

        self.clear_and_refresh()
        self.current_header += '\n\nSELECT A PLAYBOOK: '
        playbooks = self.playbook_mgr.playbook_names()
        options = playbooks.copy()
        options.append('RETURN TO MAIN MENU')
        self.current_option = 0
        self.draw_menu(options)

        while True:
            key = self.stdscr.getch()
            if key == curses.KEY_UP and self.current_option > 0:
                self.current_option -= 1
            elif key == curses.KEY_DOWN and self.current_option < len(options) - 1:
                self.current_option += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if self.current_option == len(options) - 1:  # "RETURN TO MAIN MENU" selected
                    if len(self.menu_stack) > 1:
                        self.current_menu = self.menu_stack.pop()
                    return
                else:  # Valid playbook selected
                    self.current_playbook = playbooks[self.current_option]
                    if len(self.menu_stack) > 1:
                        self.current_menu = self.menu_stack.pop()
                    return
            self.draw_menu(options)

    def add_function_menu(self):
        # Logic to handle the different actions
        # Get the list of enabled functions
        # Check to make sure that current_function is None
        if not self.current_playbook:
            self.log.debug(f"Could not add function to playbook: No playbook selected.")
            self.current_menu = self.menu_stack.pop()
            return 
        if not self.current_function:
            # Call the function selection menu
            self.log.debug(f"No current function selected. Sending used to select function menu.")
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.select_function_menu # Retrieve data from the playbook
            self.select_function_menu()

        self.build_header() # Update the header
        self.clear_and_refresh() # Clear and refresh the screen

        # Return to the previous menu if the user chose to go back
        if self.current_function == len(self.config_mgr.enabled_playbook_functions) - 1:
            self.log.debug(f"Use chose to return to previous menu.")
            self.current_menu = self.menu_stack.pop()
            return 
        
        # Get the integration name from the function name
        self.current_function = PlaybookFunction(self.current_function)

        # Get the data dependencies for the function
        self.current_menu = self.select_data_dependencies_menu
        self.select_data_dependencies_menu()    
        
        self.log.debug(f"Exiting add_function_menu")
        self.current_menu = self.menu_stack.pop()
        return   # Return to the previous menu
    
    def select_function_from_playbook(self):
        """Menu for selecting an existing function from a playbook"""
        # Always display the header
        self.build_header()
        self.clear_and_refresh()

        # Get a list of all the enabled functions
        playbook_functions = [f.name for f in self.current_playbook.logic]
        options = playbook_functions.copy()
        options.append("BACK") # append "BACK" options to list
        self.current_option = 0
        self.draw_menu(options)

        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                # Get the selected integration index from the current option
                selected_option = self.current_option
                if selected_option == len(options) - 1: # User wants to go back
                    self.current_menu = self.menu_stack.pop()
                    return
                else:
                    # Set the selected function and return to previous menu
                    self.current_function = self.current_playbook.logic[selected_option]
                    self.current_menu = self.menu_stack.pop()
                    return 
            elif key == curses.KEY_UP:
                # Navigate up the options
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                # Navigate down the options
                self.current_option = (self.current_option + 1) % len(options)
            # Update the display after each key press
            self.draw_menu(options)
            self.build_header() # Update the header
 
    def edit_function_menu(self, action='modify'):
        """Menu for adding a function to a playbook"""
        # Always display the header
        # If the user chose to modify a function, we have to figure out which one to modify from the playbook's logic
        if action == 'remove':
            # If there's only one function, just remove it
            if len(self.current_playbook.logic) == 1:
                self.current_function = self.current_playbook.logic[0]
            # Generate a list of the playbook's functions and let the user choose which one to modify
            self.current_header += '\n\nSELECT AN ACTION TO REMOVE: '
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.select_function_from_playbook
            self.select_function_from_playbook()
            if not self.current_function:
                self.log.error(f"Error removing function from playbook {self.current_playbook.name}: No function selected.")
                self.current_menu = self.menu_stack.pop()
                return   # Return to the previous menu
            # Confirm that the user wants to remove the function. Jump to confirmation menu
            self.try_to_remove_playbook()
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.playbook_review_menu
            self.playbook_review_menu()
            return
            
        elif action == 'modify':
            if len(self.current_playbook.logic) == 1:
                self.current_function = self.current_playbook.logic[0]
            else:
                # Generate a list of the playbook's functions and let the user choose which one to modify
                self.current_header += '\n\nSELECT AN ACTION TO MODIFY: '
                self.menu_stack.append(self.current_menu)
                self.current_menu = self.select_function_from_playbook
                self.select_function_from_playbook()
                if not self.current_function:
                    self.log.error(f"Error modifying function from playbook {self.current_playbook.name}: No function selected.")
                    self.current_menu = self.menu_stack.pop()
                    return   # Return to the previous menu
            # Send the user to the select trigger menu to finish modifying the function
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.select_data_dependencies_menu
            self.select_data_dependencies_menu() 
            
            # Return to the previous menu
            self.current_function = None
            self.current_menu = self.menu_stack.pop()
            return
    
    def playbook_review_menu(self):
        """Shows the user all of the options they've selected and asks them if it is correct"""
        # Always display the header
        self.current_header = self.playbook_header
        self.clear_and_refresh()
        
        self.current_header += "YOU HAVE SELECTED THE FOLLOWING OPTIONS: "
        self.current_header += f"\n\tPLAYBOOK: {self.current_playbook.name}"
        self.current_header += f"\n\tFUNCTIONS: {[function_name for function_name in self.current_playbook.get_unique_functions()]}"
        self.current_header += f"\n\tINTEGRATION_DEPENDENCIES: {[integration_name for integration_name in self.current_playbook.integration_deps]}"
        self.current_header += f"\n\tLOGIC: {self.current_playbook.visualize()}"
        self.current_header += f"\n\nIS THIS CORRECT? "
        correct = self.yes_or_no_menu()
        if correct:
            self.current_header = self.playbook_header
            self.current_menu = self.exit_playbook_menu
            self.exit_playbook_menu()
        else:
            self.current_menu = self.playbook_editor_menu
            self.playbook_editor_menu()
        return            
    
    def try_to_update_playbook(self):
        """This tries to update the playbook"""
        # Update the playbook data in memory and the global cache
        try:
            # Populate integration dependencies and functions list
            self.current_playbook.integration_deps = self.config_mgr.get_unique_integration_dependencies_by_function_list(self.current_playbook.functions)
            # Update playbook variables 
            self.current_playbook.update()
            self.playbook_mgr.update_playbook_data(self.current_playbook.name, self.current_playbook.data)
        except Exception as e: 
           self.log.error(f"No playbook to update.") 
        return
    
    def try_to_remove_playbook(self):
        """This tries to update the playbook"""
        # Update the playbook data in memory and the global cache
        try:
            self.current_playbook.remove_playbook_function(self.current_function)
            self.playbook_mgr.update_playbook_data(self.current_playbook.name, self.current_playbook.data)
        except Exception as e: 
           self.log.error(f"No playbook to remove.") 
        return

    def yes_or_no_menu(self):
        # Build menu options
        options = ["YES", "NO"]
        self.current_option = 0
        self.draw_menu(options)
        chosen_option = False
        while True:
            key = self.stdscr.getch()
            if key == curses.KEY_UP and self.current_option > 0:
                self.current_option -= 1
            elif key == curses.KEY_DOWN and self.current_option < len(options) - 1:
                self.current_option += 1
            elif key in [curses.KEY_ENTER, 10, 13]:
                if self.current_option == 0:  # YES
                    chosen_option = True
                else:  # NO
                    chosen_option = False
                return chosen_option
            # Redraw the menu and refresh the screen
            self.draw_menu(options)

    def get_integration_name_by_function(self, function_name):
        if function_name in self.config_mgr.enabled_integrations:
            return self.config_mgr.enabled_integrations[function_name]

    def select_function_menu(self):
        """Menu for adding a function to a playbook"""
        # Always display the header
        self.build_header()
        self.clear_and_refresh()
        # Get a list of all the enabled functions, and add the "HALT PLAYBOOK" option
        functions = list(self.config_mgr.enabled_playbook_functions.keys())
        options = functions.copy()
        options.insert(0, "HALT_PLAYBOOK") # prepend "HALT PLAYBOOK" to list
        options.append("BACK") # append "BACK" options to list
        
        # Initial menu draw
        self.current_option = 0
        self.draw_menu(options)
        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                # Get the selected integration index from the current option
                selected_option = self.current_option
                if selected_option == len(options) - 1:  # Last option is "BACK"
                    self.current_menu = self.menu_stack.pop()
                    return
                if selected_option == 0: # User selected "halt_playbook"
                    if self.current_function is not None and isinstance(self.current_function, PlaybookFunction):
                        self.current_header += '\n\nCANNOT HALT PLAYBOOK AS ITS FIRST ACTION'
                        continue
                    else:
                        self.current_function = 'halt_playbook'
                        self.log.debug(f"User selected halt_playbook.")
                        self.current_menu = self.menu_stack.pop()
                        return
                elif selected_option in range(1, len(functions) - 1):
                    # Set the selected function and return to previous menu
                    self.current_function = options[selected_option]
                    self.log.debug(f"User selected function {self.current_function}.")
                    self.current_menu = self.menu_stack.pop()
                    return
            elif key == curses.KEY_UP:
                # Navigate up the options
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                # Navigate down the options
                self.current_option = (self.current_option + 1) % len(options)
            # Update the display after each key press
            self.build_header() # Update the header 
            self.draw_menu(options)
     
    def select_data_dependencies_menu(self):
        """Menu for selecting data dependencies for a function"""
        self.build_header()
        self.clear_and_refresh()

        # List of potential data dependencies 
        self.log.debug(f'Getting data dependencies list for function {self.current_function.name}')
        data_deps = self.config_mgr.get_data_dependencies_by_function(self.current_function.name)
        options = data_deps.copy()
        options.insert(0, "None") # prepend "None" to list
        options.append("Back") # append "BACK" options to list
        self.log.debug(f'Current options for select_data_dependencies_menu: {options}')
        self.current_option = 0
        self.draw_menu(options)

        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                selected_option = self.current_option
                if selected_option == len(options) - 1:  # "BACK" selected
                    self.current_function = None
                    self.current_menu = self.menu_stack.pop()
                    return
                
                elif selected_option == 0:  # No dependencies
                    self.current_function.data_dependencies = None
                    self.log.debug(f"User selected no data dependencies.")
                else:
                    # User selects a dependency
                    if self.current_function.data_dependencies is None:
                        self.current_function.data_dependencies = []
                    self.current_function.data_dependencies.append(options[selected_option])
                    self.log.debug(f"User selected data dependency {options[selected_option]}")
                    # Call the trigger selection menu
                self.current_menu = self.select_trigger_menu
                self.log.debug(f"Sending user to select_trigger_menu.")
                self.select_trigger_menu()
                
            elif key == curses.KEY_UP:
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                self.current_option = (self.current_option + 1) % len(options)

            self.draw_menu(options)

    def select_trigger_menu(self):
        """Add or remove a function trigger"""
        # The header is always displayed
        self.build_header()
        self.clear_and_refresh()

        # Options for trigger types
        options = ["CONTINUOUS", "TIME INTERVAL", "CONDITION", "BACK"]
        self.current_option = 0
        self.draw_menu(options)

        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                selected_option = self.current_option
                if selected_option == 0:  # CONTINUOUS
                    self.current_function.trigger_type = 'always'
                    self.log.debug(f"User selected continuous trigger.")
                    
                elif selected_option == 1:  # TIME INTERVAL
                    self.current_function.trigger_type = 'time'
                    self.current_function.trigger_duration = self.get_user_input_for_time_interval()
                    self.log.debug(f"User selected time interval of {self.current_function.trigger_duration} seconds.")
                    
                elif selected_option == 2:  # CONDITION (Not implemented)
                    self.stdscr.addstr("\nCONDITION trigger is not supported yet.\n")
                    continue
                
                elif selected_option == 3:  # BACK (Go back to playbook_editor_menu)
                    self.current_function = None
                    self.current_menu = self.menu_stack[-2]
                    return
                
                # Call the success menu
                self.current_menu = self.edit_on_success_menu
                self.edit_on_success_menu()
            elif key == curses.KEY_UP:
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                self.current_option = (self.current_option + 1) % len(options)
            # Update the display after each key press
            self.draw_menu(options)
            
    def edit_on_success_menu(self):
        """Calls the edit_on_success_menu() twice to ensure that both settings are set"""       
        # User chose to go back or an error occurred
        if not self.current_function:
            self.log.debug(f"User chose to go back or an error occurred.")
            self.log.error(f"Error editing playbook: No playbook selected.")
            self.current_menu = self.menu_stack[-2]
            return
        
        self.log.debug(f"Menu stack upon getting to edit_on_success_menu: {self.menu_stack}")
        # First time user is visiting this menu for this function
        # Set fail attribute
        self.menu_stack.append(self.current_menu)
        self.current_menu = self.set_success_and_fail
        self.set_success_and_fail('\n\nWHAT SHOULD HAPPEN IF THIS ACTION FAILS?')
        self.current_function.on_fail = self.current_success_or_fail
        self.current_success_or_fail = None
        
        # Set success attribute
        self.menu_stack.append(self.current_menu)
        self.current_menu = self.set_success_and_fail
        self.set_success_and_fail('\n\nWHAT SHOULD HAPPEN IF THIS ACTION EXECUTES SUCCESSFULLY?')
        self.current_function.on_success = self.current_success_or_fail
        self.current_success_or_fail = None
        self.log.debug(f"User chose to {self.current_function.on_success} if the action succeeds and {self.current_function.on_fail} if the action fails.")
        
        # Handle what to do if the user chose to loop or execute next action
        if self.current_function.on_success == 'halt_playbook':
            # User is done building their playbook and is ready to save and exit
            final_func = PlaybookFunction('halt_playbook', trigger={'type': 'always'})
            self.current_playbook.add_playbook_function(final_func)
        else:
            if len(self.menu_stack) < 3:
                self.menu_stack.append(self.current_menu)
            self.loop_or_execute_next_action()
        
        self.try_to_update_playbook() # Update the playbook data in memory
        # Jump to the save menu, user should be done building their playbook
        self.current_menu = self.playbook_review_menu
        self.playbook_review_menu()
        return
        
    def loop_or_execute_next_action(self):
        """Handle looping or executing the next action based on user choice."""
        option = 'next' if self.current_function.on_success == 'next' or self.current_function.on_fail == 'next' else 'loop'
        success = self.current_function.on_success == option
        self.log.debug(f"In loop_or_execute_next_action: option is '{option}' and success is '{success}'.")
        self.log.debug(f"Sending user to select_next_function_menu.")
        self.select_next_function_menu(success, option)

    def set_success_and_fail(self, header_add_on):
        """Menu for adding or removing an on_success trigger"""
        # Clear and refresh the header
        self.build_header()
        self.current_header += header_add_on
        self.clear_and_refresh()
        
        # Prepend list with "HALT PLAYBOOK" option
        options = ["HALT PLAYBOOK", "EXECUTE NEXT ACTION", "LOOP TO PREVIOUS ACTION", "BACK"]
        self.current_option = 0
        self.draw_menu(options)
        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                # Get the selected integration index from the current option
                selected_option = self.current_option
                if selected_option == 0:  # HALT PLAYBOOK
                    # Update the on_success attribute                    
                    self.current_success_or_fail = 'halt_playbook' # Append the function to the playbook logic
                elif selected_option == 1:  # EXECUTE NEXT ACTION
                    self.current_success_or_fail = 'next'
                elif selected_option == 2:  # LOOP TO PREVIOUS ACTION
                    self.current_success_or_fail = 'loop'
                elif selected_option == 3:  # BACK
                    self.current_function = None
                    self.current_menu = self.menu_stack[-2] # Go back to playbook_editor_menu
                    return
                self.current_menu = self.menu_stack.pop()
                return
            elif key == curses.KEY_UP:
                # Navigate up the options
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                # Navigate down the options
                self.current_option = (self.current_option + 1) % len(options)
            # Update the display after each key press
            self.build_header() # Update the header
            self.current_header += header_add_on
            self.draw_menu(options)
    
    def select_next_function_menu(self, success, option):
        """Handle user's choice to execute the next action or loop to a previous action."""
        temp_function = self.current_function # Store the current function temporarily
        self.current_function = None # Set the current function to None
        self.log.debug(f"Menu stack before looping: {self.menu_stack}")
        self.menu_stack.append(self.current_menu)
        self.log.debug(f"Current playbook logic before looping: {self.current_playbook.logic}")
        
        if option == 'next': # User want to select a function to run next
            self.log.debug(f"Sending user to select_function_menu.")
            self.current_menu = self.select_function_menu # Get the next function name
            self.select_function_menu()
            
            if success:
                temp_function.on_success = self.current_function
            else:
                temp_function.on_fail = self.current_function

            # Add the updated function back to the playbook logic
            self.current_playbook.add_playbook_function(temp_function)
            self.log.debug(f"Current playbook logic after adding temp function: {self.current_playbook.logic}")
            self.try_to_update_playbook() # Update the playbook data in memory
            self.current_menu = self.add_function_menu
            self.add_function_menu()

        elif option == 'loop':
            # User wants to loop to a previous function
            if len(self.current_playbook.logic) > 1:
                # Allow user to pick the previous function to loop to
                self.log.debug(f"Sending user to select_function_from_playbook.")
                self.current_menu = self.select_function_from_playbook
                self.select_function_from_playbook()
                self.log.debug(f"User chose to loop to function {self.current_function.name} is success is {success}.")
                self.log.debug(f"Current playbook logic: {self.current_playbook.logic}")
                
                # Update the current function's on_success or on_fail attribute
                if success:
                    temp_function.on_success = self.current_function.name
                else:
                    temp_function.on_fail = self.current_function.name
                # Add the updated function back to the playbook logic
                self.current_playbook.add_playbook_function(temp_function)
                self.log.debug(f"Current playbook logic after adding temp function: {self.current_playbook.logic}")
                self.try_to_update_playbook() # Update the playbook data in memory
                self.current_function = None # Reset the current_function
            else:
                self.log.error("No previous function to loop to.")
                self.current_menu = self.menu_stack.pop()
                return

            # Append a 'halt_playbook' function if it's not already there
            self.log.debug(f"Name of last logic function: {self.current_playbook.logic[-1].name}")
            if self.current_playbook.logic[-1].name != 'halt_playbook':
                final_func = PlaybookFunction('halt_playbook', trigger={'type': 'always'})
                self.current_playbook.add_playbook_function(final_func)

        self.log.debug(f"Current playbook logic after looping: {self.current_playbook.logic}")
        self.log.debug(f"Menu stack after looping: {self.menu_stack}")
        self.log.debug(f"Returning to playbook_editor_menu.")
        self.current_menu = self.menu_stack.pop()
        return

    # Terminal Functions
    def exit_playbook_menu(self):
        """Menu asking the user if they want to save their playbook"""
        # Turn off cursor blinking
        self.build_header() # Update the header
        self.clear_and_refresh()
        self.current_header += '\n\nSAVE YOUR PROGRESS? ' # Add the prompt to the header

        # Build menu options
        confirm = self.yes_or_no_menu()
        if confirm:
            # Enable playbook
            self.current_playbook.enabled = True
            # Update the playbook properties in memory 
            self.try_to_update_playbook()
            # Write the playbook to file
            self.playbook_mgr.save_playbook(self.current_playbook.name)
            # Update configuration manager with the new playbook
            self.config_mgr.update_enabled_items()
        # Reset the current_playbook variable
        self.current_playbook = None
        self.menu_stack = [self.menu_stack[0]] # Reset the menu stack
        self.current_menu = self.main_menu
        self.main_menu() # Return to the main menu
    
    # Helper Functions
    def get_user_input_for_time_interval(self):
        """Gets the user input for a time interval trigger."""
        # Prompt the user for the time interval in seconds
        interval = self.draw_input_prompt("SELECT A TIME INTERVAL (IN SECONDS, DEFAULT IS 60)>>>  ")
        try:
            # Convert the interval to an integer
            interval = int(interval)
        except ValueError:
            # If the interval is not an integer, set it to the default of 60
            interval = 60
        return interval
    
    # Playbook Launcher
    def launch_playbook_menu(self):
        """This asks the user to select a playbook to launch."""
        self.current_header += '\nPLAYBOOK>>> (LAUNCH)'
        self.menu_stack.append(self.current_menu)
        self.current_menu = self.select_playbook_menu
        self.select_playbook_menu()
        # Assuming select_playbook_menu will update self.current_playbook
        # Wait for the user to select a playbook...

        if self.current_playbook:
            if isinstance(self.current_playbook, str):
                self.current_playbook = Playbook(self.current_playbook)
            if self.current_playbook.is_running:
                self.current_header += '\n\nPLAYBOOK IS ALREADY RUNNING'
            else:
                try:
                    self.playbook_mgr.launch_playbook(self.current_playbook.name, self.config_mgr, once=True)
                    self.try_to_update_playbook()
                    self.log.info(f"Launched playbook {self.current_playbook.name}")
                except Exception as e:
                    self.current_header += '\n\nERROR LAUNCHING PLAYBOOK'
                    self.log.error(f"Error launching playbook {self.current_playbook.name}: {e}")
                    self.log.error(f"An error has occurred: {traceback.format_exc()}")
        else:
            self.log.error(f"Error launching playbook: No playbook selected.")

        # After handling the playbook, return to the previous menu
        self.current_menu = self.menu_stack.pop()
        return

    # Playbook Stopper
    def stop_playbook_menu(self):
        """This asks the user to select a playbook to stop"""
        # Update the header, then jump to select playbook menu 
        self.current_header += '\nPLAYBOOK>>> (STOP)'
        self.current_menu = self.select_playbook_menu
        self.select_playbook_menu()
        if self.current_playbook is None:
            # User chose to go back or an error occurred
            self.current_menu = self.menu_stack[-1]
            return 
        elif self.current_playbook:
            if isinstance(self.current_playbook, str):
                self.current_playbook = Playbook(self.current_playbook)
            if self.current_playbook.is_running:
                try:
                    self.log.debug(f"User chose to stop playbook {self.current_playbook.name}")
                    self.current_playbook.stop()
                    self.try_to_update_playbook()
                    self.playbook_mgr.update_playbook_data(
                        self.current_playbook.name, self.current_playbook.data
                    )
                    self.current_menu = self.menu_stack[-1]
                except Exception as e:
                    self.current_header += '\n\nERROR STOPPING PLAYBOOK'
                    self.log.error(f"Error stopping playbook {self.current_playbook.name}: {e}")
                    self.log.error(f"An error has occurred: {traceback.format_exc()}")
                    self.current_menu = self.menu_stack.pop()
                return
            else:
                self.log.info(
                    f"Playbook {self.current_playbook.name} is not running. Cannot stop it."
                )
                self.current_header += '\n\nPLAYBOOK IS NOT RUNNING'
                self.current_menu = self.menu_stack[-1]
                return

    # Playbook Removal
    def remove_playbook_menu(self):
        # Update the header, then jump to select playbook menu
        self.current_header += '\nPLAYBOOK>>> (REMOVE)'
        self.current_menu = self.select_playbook_menu
        self.select_playbook_menu()
        if self.current_playbook is None:
            self.current_menu = self.menu_stack.pop() # If the user chose to go back or an error occurred
            return
        else:
            # Remove the playbook from the playbook manager
            self.log.debug(f"User chose to remove playbook {self.current_playbook.name}")
            try:
                self.config_mgr._disable_playbook(self.current_playbook.name)
                # Update the playbook data in memory and the global cache
                self.try_to_update_playbook()
                self.playbook_mgr.update_playbook_data(self.current_playbook.name, self.current_playbook.data)
            except Exception as e:
                self.current_header += '\n\nERROR REMOVING PLAYBOOK'
                self.log.error(f"Error removing playbook {self.current_playbook.name}: {e}")
                # Log traceback data
                self.log.error(f"An error has occurred: {traceback.format_exc()}")
            self.current_menu = self.menu_stack.pop()
            return
        
    # Configuration 
    def configuration_menu(self):
        """Menu for editing integration configurations"""                                                                                           
        self.clear_and_refresh() # Refresh and clear the screen 
        self.build_config_header() # Update the header
        options = ['ADD TOOL', 'REMOVE TOOL', 'EDIT TOOL', 'BACK']
        self.current_option = 0
        self.draw_menu(options)
        while True:
            key = self.stdscr.getch()
            if key == curses.KEY_UP and self.current_option > 0:
                self.current_option -= 1
            elif key == curses.KEY_DOWN and self.current_option < len(options) - 1:
                self.current_option += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if self.current_option == 0:  # Add integration
                    self.menu_stack.append(self.current_menu)
                    self.current_menu = self.edit_integration
                    self.edit_integration(action='add')
                    return
                elif self.current_option == 1:  # Remove integration
                    if len(self.config_mgr.integrations_list) == 0:
                        self.current_header += '\n\nNO TOOLS TO REMOVE'
                        continue
                    self.menu_stack.append(self.current_menu)
                    self.current_menu = self.edit_integration
                    self.edit_integration(action='remove')
                    return
                elif self.current_option == 2:  # Update integration
                    if len(self.config_mgr.integrations_list) == 0:
                        self.current_header += '\n\nNO TOOLS TO EDIT'
                        continue
                    self.menu_stack.append(self.current_menu)
                    self.current_menu = self.edit_integration
                    self.edit_integration(action='edit')
                    return
                elif self.current_option == 3:  # Return to main menu
                    self.current_menu = self.menu_stack.pop()
                    return
            elif key == ord('q'):
                self.current_menu = self.menu_stack.pop()
                return
            # Refresh integrations list in case it was updated
            self.build_config_header() # Update the header
            self.draw_menu(options)

    def edit_integration(self, action):
        """Submenu for adding or removing an integration"""
        self.menu_stack.append(self.current_menu)
        self.current_menu = self.select_integration
        self.select_integration()
        # Initialize the integration
        self.current_integration = Integration(self.current_integration)
        # Process based on which option the user selected
        if action == 'add': # User wants to enabled a currently disabled integration 
            self.log.debug(f"User chose to add integration {self.current_integration.name}")
            confirm = self.confirm_integration_options(warning=False)
            if confirm:
                self.config_mgr._add_integration(self.current_integration.name)
                self.config_mgr.update_enabled_items()
            self.current_menu = self.menu_stack.pop()
            return
        elif action == 'remove': 
            self.log.debug(f"User chose to remove integration {self.current_integration.name}")
            confirm = self.confirm_integration_options(warning=True)
            if confirm: # User chose to remove the integration
                self.config_mgr._remove_integration(self.current_integration)
                self.config_mgr.update_enabled_items()
            self.current_menu = self.menu_stack.pop()
            return
        elif action == 'edit':
            self.log.debug(f"User chose to edit integration {self.current_integration.name}")
            self.menu_stack.append(self.current_menu)
            self.current_menu = self.update_integration
            self.update_integration()
            confirm = self.confirm_integration_options(warning=True)
            if confirm: # User chose to edit the integration
                self.config_mgr._update_integration(self.current_integration)
                self.config_mgr.update_enabled_items()
            self.current_menu = self.menu_stack.pop()
            return # Return to previous menu
        else:
            self.log.error(f"Error editing integration: Invalid action {action}")
            self.current_menu = self.menu_stack.pop()
            return # Return to previous menu
        
    def build_config_header(self, warning=False):
        """Generates the header depending on what is selected"""
        self.current_header = self.config_header
        if self.current_integration is None:
            self.current_header += f"\nTOOLBOX>>> {', '.join(self.config_mgr.enabled_integrations_list)}"
        elif self.current_integration:
            self.current_header += f"\nTOOLBOX>>> (CONFIG)"
            self.current_header += f"\n\tTOOL>>> {self.current_integration}"
        elif self.current_integration and warning == True:
            self.current_header += f"\nTOOLBOX>>> (CONFIG)"
            self.current_header += f"\n\tTOOL>>> {self.current_integration}"
            self.current_header += '\n\nWARNING: Modifying the configuration file only makes changes to the integration in memory.'
            self.current_header += '\nWARNING: You must edit the configuration file in the "./config" directory in order to make'
            self.current_header += '\nthese changes permanent.\n'
        
    def select_integration(self, new=False):
        """Generates a menu list of integrations to select from"""
        # Clear and refresh the screen 
        self.clear_and_refresh()
        # Add prompt to header 
        self.current_header += '\n\nSELECT A TOOL: '
        # Get a list of all available integrations
        if new:
            options = self.config_mgr.integrations_list.copy()
        else:
            options = self.config_mgr.enabled_integrations_list.copy()
        # Prepend list with "BACK"
        options.append("BACK")
        
        # Draw menu 
        self.current_option = 0
        self.draw_menu(options)
        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                # Get the selected integration index from the current option
                selected_option = self.current_option
                if selected_option == len(options) - 1:
                    # User chose to go back
                    self.current_menu = self.menu_stack.pop()
                    return
                else:
                    # Set the current integration and return to previous menu
                    self.current_integration = options[selected_option]
                    self.current_menu = self.menu_stack.pop()
                    return
            elif key == curses.KEY_UP:
                # Navigate up the options
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                # Navigate down the options
                self.current_option = (self.current_option + 1) % len(options)
            # Update the display after each key press
            self.draw_menu(options)

    def update_integration(self):
        """Menu to select an item to update"""
        # Clear and refresh the screen and build the header
        self.clear_and_refresh()
        self.build_config_header()
        # Build menu options
        options = ['UPDATE API KEY', 'UPDATE URL', 'UPDATE SSL', 'UPDATE CERTIFICATE VERIFICATION', 'BACK']
        self.current_option = 0
        self.draw_menu(options)
        while True:
            key = self.stdscr.getch()
            if key in [curses.KEY_ENTER, 10, 13]:
                # Get the selected integration index from the current option
                selected_option = self.current_option
                if selected_option == len(options) - 1:
                    # User chose to go back
                    self.current_menu = self.menu_stack.pop()
                    return
                elif selected_option == 0: # Update API Key
                    self.log.info(f"Updating API Key for integration {self.current_integration.name}")
                    self.log.debug(f"User select to update API Key: {self.current_integration.api_key}")
                    self.current_integration.api_key = self.draw_input_prompt("ENTER API KEY>>>  ")
                    self.log.debug(f"Updated API Key: {self.current_integration.api_key}")
                elif selected_option == 1: # Update URL
                    self.log.info(f"Updating URL for integration {self.current_integration.name}")
                    self.log.debug(f"User select to update URL: {self.current_integration.url}")
                    self.current_integration.url = self.draw_input_prompt("ENTER URL>>>  ")
                    self.log.debug(f"Updated URL: {self.current_integration.url}")
                elif selected_option == 2: # Update SSL
                    self.log.info(f"Updating SSL for integration {self.current_integration.name}")
                    self.log.debug(f"User select to update SSL: {self.current_integration.ssl}")
                    self.current_header += '\n\nENABLE SSL?:  '
                    self.current_integration.ssl = self.yes_or_no_menu()
                    self.log.debug(f"Updated SSL: {self.current_integration.ssl}")
                elif selected_option == 3: # Update CERTIFICATE VERIFICATION
                    self.log.info(f"Updating CERTIFICATE VERIFICATION for integration {self.current_integration.name}")
                    self.log.debug(f"User select to update CERTIFICATE VERIFICATION: {self.current_integration.verifycert}")
                    self.current_header += '\n\nVERIFY CERTIFICATE?:  '
                    self.current_integration.verifycert = self.yes_or_no_menu()
                elif selected_option == 4: # BACK
                    self.current_menu = self.menu_stack.pop()
                    return
            elif key == curses.KEY_UP:
                # Navigate up the options
                self.current_option = (self.current_option - 1) % len(options)
            elif key == curses.KEY_DOWN:
                # Navigate down the options
                self.current_option = (self.current_option + 1) % len(options)
            # Update the display after each key press
            self.build_config_header() # Rebuild the header
            self.draw_menu(options)

    def confirm_integration_options(self, warning=False):
        """Display the current integration options to the user and ask them to confirm"""
        # Clear and refresh the screen and build the header
        self.clear_and_refresh()
        self.build_config_header(warning=warning)
        self.log.debug(f"User selected {self.current_integration.name} prior to entering the config config menu")
        self.current_header += f"\n\nENABLED: {self.current_integration.enabled}"
        self.current_header += f"\nAPI_KEY: {self.current_integration.api_key}"
        self.current_header += f"\nURL: {self.current_integration.url}"
        self.current_header += f"\nSSL: {self.current_integration.ssl}"
        self.current_header += f"\nVERIFY_CERT: {self.current_integration.verifycert}"
        self.current_header += f"\n\nIS THIS CORRECT? "
        confirm = self.yes_or_no_menu()
        # User wants to update the integration
        return confirm
        
    # Helper Functions
    @property 
    def non_template_playbooks(self):
        return [playbook for playbook in self.playbook_mgr.playbook_names if playbook != 'playbook_template']
    
    @property
    def get_previous_function_name(self):
        if self.current_playbook.logic:
            return self.current_playbook.logic[-1].name
        return None
    
    @property
    def render_playbooks(self):
        """Renders the list of playbooks in the playbook directory"""
        return ','.join(self.playbook_mgr.playbook_names())

    @property
    def config_mgr(self):
        if not self._config_mgr:
            try:
                self._config_mgr = ConfigurationManager()
            except Exception as e:
                print(f"Error initializing application: {e}")
        return self._config_mgr
    
    @property
    def playbook_mgr(self):
        if not self._playbook_mgr:
            self._playbook_mgr = self._config_mgr.playbook_mgr
        return self._playbook_mgr
    
    @property
    def top_header(self):
        header  =  '                   ____  ______   ___    ____      ______   ___  ___    __              ' + '\n'
        header +=  '                  / __ \\/ __/ /  /   |  / __ \\    / ____/  / _ \\/ _ \\   \\ \\             ' + '\n'
        header +=  '                 / /_/ / /_ /  / /| | / /_/ /   / / __   / , _/ // /    > >            ' + '\n'
        header +=  '                 \\____/\\__/___/_/ |_|/_____/   /_/ /_/  /_/|_/____/    /_/             ' + '\n'
        header +=  '                 A SOAR APPLICATION LIGHTWEIGHT ENOUGH FOR ANY ENVIRONMENT              ' + '\n'
        return header

    @property
    def welcome_header(self):
        header =    '                                    _                                                               ' + '\n'                                                                                                
        header +=   '                _______ _________  ( )   _______           _______  _______  ______                 ' + '\n'   
        header +=   '               (  ____ )\__   __/  | |  (  ____ \|\     /|(  ___  )(  ____ )(  __  \                ' + '\n'   
        header +=   '               | (    )|   ) (     | |  | (    \/| )   ( || (   ) || (    )|| (  \  )               ' + '\n'
        header +=   '               | (____)|   | |     (_)  | (_____ | | _ | || |   | || (____)|| |   ) |               ' + '\n'
        header +=   '               |  _____)   | |      _   (_____  )| |( )| || |   | ||     __)| |   | |               ' + '\n'
        header +=   '               | (         | |     ( )        ) || || || || |   | || (\ (   | |   ) |               ' + '\n'
        header +=   '               | )      ___) (___  | |  /\____) || () () || (___) || ) \ \__| (__/  )               ' + '\n'
        header +=   '               |/       \_______/  | |  \_______)(_______)(_______)|/   \__/(______/                ' + '\n'
        header +=   '   _____ ____  ___    ____         (_)...             ...                   __________  ____________' + '\n'
        header +=   '  / ___// __ \/   |  / __ \      :!JYPPPPPP5J!.  ^?55PPPPP5Y?~             / ____/ __ \/ ____/ ____/' + '\n'
        header +=   '  \__ \/ / / / /| | / /_/ /      Y&5JJJJJ?JJYPG~YB5YJ??JJJJYG&:           / __/ / / / / / __/ __/   ' + '\n'
        header +=   ' ___/ / /_/ / ___ |/ _, _/       !&Y??JJYYYJ?75@#??JYYYYJ???BG           / /___/ /_/ / /_/ / /___   ' + '\n'
        header +=   '/____/\____/_/  |_/_/ |_|         ?#5????JJ5PPB@&GPPYJ????JGG:     _   _/_____/_____/\____/_____/   ' + '\n'
        header +=   '                    ____  ____     ^5G5YJJJYB@@@@@@PJJJJYPP?.     / /_/ /_  ___                     ' + '\n'
        header +=   '                   / __ \/ __ \      .Y&#BG#@&BBGBB#@&BB#@B~     / __/ __ \/ _ \                    ' + '\n'
        header +=   '                  / /_/ / / / /    !#BGPG#@&GPPPPPPB@#GPGB@5.   / /_/ /~/ /  __/                    ' + '\n'
        header +=   '                  \____/_/ /_/    .&#GB&&&############&#BPB@?   \__/_/ /_/\___/                     ' + '\n'
        header +=   '                                 ^5&&@@#GPPPPG#@@GPPPPPG#@&&#7          ~^                          ' + '\n'
        header +=   '        .::^^~~~~~~~~~~~~~~~~~~~J&BPB@BPPPPPPPG@&PPPPPPPP&#PG&G~~~~~~~!77!!!77777!!!7~^~~7:         ' + '\n'
        header +=   "        '::^^~~!!!!!7777777777?@BPPB@BPPPPPPG&@@BGPPPPPP&#PPG@P77777?7?Y7^^~~~~~~~~~^:^^~7:         " + '\n'
        header +=   '                                B#PG&@@#BGGB########BBB#&@&GP#@!        7!                          ' + '\n'
        header +=   '                                 .#&PPPGB&@BPPPPPPPP#@BPPPPB@?         :^                           ' + '\n'
        header +=   '                                  !@BPPPPG&&BGPPPPGB&GPPPPG&G          ~                            ' + '\n'
        header +=   '                                   !G#BGGG&@@&####&@&GGGB##Y.                                       ' + '\n'
        header +=   '                                     ^?P#@@&GGGGGGGB@@&BY!.                                         ' + '\n'
        header +=   '                                        :~?GBBBBBB#B57^                                             ' + '\n'
        header +=   '                                            ^!?JJ7~.                                                ' + '\n'
        return header

    @property 
    def config_header(self):
        header =  '   _________  _  _________________  _____  ___ ______________  _  __  _______  ______________  ___  ' + '\n'
        header += '  / ___/ __ \/ |/ / __/  _/ ___/ / / / _ \/ _ /_  __/  _/ __ \/ |/ / / __/ _ \/  _/_  __/ __ \/ _ \ ' + '\n'
        header += ' / /__/ /_/ /    / _/_/ // (_ / /_/ / , _/ __ |/ / _/ // /_/ /    / / _// // // /  / / / /_/ / , _/ ' + '\n'
        header += ' \___/\____/_/|_/_/ /___/\___/\____/_/|_/_/ |_/_/ /___/\____/_/|_/ /___/____/___/ /_/  \____/_/|_|  ' + '\n'
        return header

    @property
    def playbook_header(self):
        header =   '           ___  __   _____  _____  ____  ____  __ __  ________  _______ __________  ___            ' + '\n'
        header +=  '          / _ \/ /  / _ \ \/ / _ )/ __ \/ __ \/ //_/ / ___/ _ \/ __/ _ /_  __/ __ \/ _ \           ' + '\n'
        header +=  '         / ___/ /__/ __ |\  / _  / /_/ / /_/ / ,<   / /__/ , _/ _// __ |/ / / /_/ / , _/           ' + '\n'
        header +=  '        /_/  /____/_/ |_|/_/____/\____/\____/_/|_|  \___/_/|_/___/_/ |_/_/  \____/_/|_|            ' + '\n'                                                                                                                 
        return header
