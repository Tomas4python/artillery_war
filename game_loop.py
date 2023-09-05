import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import random
import os
import tempfile

# Import application modules
from console import Console, WeatherConditions, SituationReport, ShotParameterInput, UnitStatus
from map import Map
from radar import Radar
from settings import Settings, SoundManager
from setup import GameSetup
from units import Unit
from calculations import Shot

############################
##### Game loop module #####
############################

# <game_loop>
#     -Game setup
#        <round_loop>:
#           -Round setup
#           -Open: war statistics, map, radar and console
#           -Make multiple turns: shoot and check for active units
#           -Show battle results
#           -Close: map, radar and console
#           -Show war statistics
#        </round_loop>
#     -Show end game message
# </game_loop>

class Play:
    """A class for the main loop of the game"""

    def __init__(self, main_instance_reference):
        self.main = main_instance_reference
        self.shot = Shot()
        # Initialize mixer for game sound
        self.sound_manager = SoundManager()

    def play_the_game(self, event=None):
        """Function for game and round setup, to open game windows and set navigation among windows"""

        # Setup the game
        if Settings.game == False:
            self.setup = GameSetup(self)
            # Set stage of the game
            Settings.game = True
            # Remove previous game end stage
            Settings.war_results = False
            Settings.end_war_results = False
            # Show initial statistic in the beginning of the game
            self.show_war_results()
        
        # Check if the game should end
        if self.setup.game_should_end():
            self.show_war_end_results(self.setup.defender_total_damage, self.setup.intruder_total_damage)
        else:
            # Start counting battles
            Settings.battle_index += 1
        
            # Bring root window on top of others
            self.main.root.attributes('-topmost', 1)

            # Add a label with typing effect above war results
            def type_label_text(label, text, index=0):
                """Typing effect"""
                if index < len(text):
                    label.configure(text=label.cget("text") + text[index])
                    self.sound_manager.play_sound('typing', delay=0)
                    label.after(50, type_label_text, label, text, index+1)

            self.battle_no_label = ctk.CTkLabel(master=self.main.root, text="ENTER THE", fg_color="#3D5328", text_color="black", font=("Courier New", 70, "bold"), padx=15)
            self.battle_no_label.place(relx=0.5, rely=0.15, anchor='center')

            # Setup the round
            self.weather_conditions, self.units, map_path, radar_path, self.map_direction = self.setup.round_setup()
            self.all_units_list = self.units['Defender'] + self.units['Intruder']
            self.turn_index = 0

            # Setup initial empty list of targets for computer
            self.target_units = [] 
            
            # Open console view
            self.console = Console(self.main.root)
            WeatherConditions(self.console.main_frame, self.weather_conditions)
            self.situation_report = SituationReport(self.console.main_frame)
            self.situation_report.insert_message(f"             {Settings.call_sign}, WELCOME!")
            self.shot_parameter_input = ShotParameterInput(self.console.main_frame, self.situation_report, self, self.units)
            self.unit_status = UnitStatus(self.console.main_frame, self.units)
            self.situation_report.insert_message(f"      ----- ----- BATTLE #{Settings.battle_index} ----- -----")

            # Open drone view if defender
            if Settings.player_role == 'Defender':
                self.map_drone = Map(self.main.root, map_path)
                # Add units to the map
                for unit in self.all_units_list:
                    self.map_drone.add_unit(unit)

            # Open radar view
            self.radar = Radar(self.main.root, radar_path, self.map_direction, self.weather_conditions["Wind Direction,(°)"], self.situation_report)
            # Add units to the radar
            for unit in self.all_units_list:
                if unit.unit_type == 'artillery':
                    self.radar.add_unit(unit)
            
            # Hide other windows behind root
            if Settings.player_role != 'Intruder':
                self.map_drone.map_window.attributes('-topmost', 0)
            self.radar.radar_window.attributes('-topmost', 0)
            self.console.console.attributes('-topmost', 0)
            
            # Show battle number above war report
            self.battle_no_label.configure(text="")
            type_label_text(self.battle_no_label, f"BATTLE #{Settings.battle_index}")

            # Bind keyboard keys for navigation among console, drone, radar and war results
            self.main.root.unbind_all('c')
            if Settings.player_role != 'Intruder':
                self.main.root.bind_all('d', self.raise_map)
            else:
                # Intruder does not have drones
                self.main.root.bind_all('d', self.message_about_drone)
                self.message_about_drone = self.select_message_about_drone()
            self.main.root.bind_all('r', self.raise_radar)
            self.main.root.bind_all('c', self.raise_console)
            self.main.root.bind_all('s', self.raise_menu)
            self.main.root.bind_all('w', self.withdraw)

    def raise_map(self, event=None):
        """Drone view on top"""
        
        self.main.root.attributes('-topmost', 0)
        if Settings.player_role != 'Intruder':
            self.map_drone.map_window.attributes('-topmost', 1)
        self.radar.radar_window.attributes('-topmost', 0)
        self.console.console.attributes('-topmost', 0)
        self.map_drone.map_window.focus()

    def raise_menu(self, event=None):
        """Result window on top"""

        self.main.root.attributes('-topmost', 1)
        if Settings.player_role != 'Intruder':
            self.map_drone.map_window.attributes('-topmost', 0)
        self.radar.radar_window.attributes('-topmost', 0)
        self.console.console.attributes('-topmost', 0)
        self.main.root.focus()

    def raise_radar(self, event=None):
        """Radar view on top"""
        
        self.main.root.attributes('-topmost', 0)
        if Settings.player_role != 'Intruder':
            self.map_drone.map_window.attributes('-topmost', 0)
        self.radar.radar_window.attributes('-topmost', 1)
        self.console.console.attributes('-topmost', 0)
        self.radar.radar_window.focus()

    def raise_console(self, event=None):
        """Console view on top"""

        self.main.root.attributes('-topmost', 0)
        if Settings.player_role != 'Intruder':
            self.map_drone.map_window.attributes('-topmost', 0)
        self.radar.radar_window.attributes('-topmost', 0)
        self.console.console.attributes('-topmost', 1)
        self.console.console.focus()

    def withdraw(self, event=None):
        """Function to manage withdrawal from the battle key"""

        # Check if battle is still ongoing
        if Settings.battle_results:
            self.situation_report.insert_message("\n     Moving to new positions!")
        else:
            def withdraw_consequences():
                """Close the battle on withdrawal"""

                # Make all player units inactive
                if Settings.player_role == "Defender":
                    player_units = self.units["Defender"]
                else:
                    player_units = self.units["Intruder"]
                for unit in player_units:
                    unit.is_active = False
                self.show_battle_results()

            def on_yes(event):
                """If positive answer"""
                if event.char == 'y':
                    self.console.console.unbind("<Key>", key_binding_id)
                    if Settings.player_role == "Defender":
                        self.situation_report.insert_message("\n     We pack up and retreat.")
                    if Settings.player_role == "Intruder":
                        self.situation_report.insert_message("\n     Let everything burn in HELL, we're getting out of here, every man for himself!")
                    # Give time to read message
                    self.console.console.after(3000, withdraw_consequences)

            def on_other_key(event):
                """If negative answer"""
                if event.char != 'y':
                    self.console.console.unbind("<Key>", key_binding_id)
                    if Settings.player_role == "Defender":
                        self.situation_report.insert_message("\nWe have no possibility to retreat from the battlefield without losing equipment, we will make last shots and retreat.")
                    if Settings.player_role == "Intruder":
                        self.situation_report.insert_message("\nWe will heroically sacrifice our lives for the honor of the Motherland, we will fight to the last.")

            self.raise_console()

            # If player press withdrawal from the battle key
            if Settings.player_role == "Defender":
                self.situation_report.insert_message(f"\n{Settings.call_sign}, you received an order from the direct military commander to retreat. Do you still have a possibility to retreat? y/n?")
            if Settings.player_role == "Intruder":
                self.situation_report.insert_message(f"\n{Settings.call_sign}, you received an order from the direct military commander to fight until the last drop of blood. Will you disobey orders and flee the battlefield? y/n?")
            
            # Bind the keys and keep the ID
            key_binding_id = self.console.console.bind("<Key>", lambda event: on_yes(event) if event.char == 'y' else on_other_key(event))

    def message_about_drone(self, event):
        """Show message for intruder instead of drone view"""

        self.raise_console()
        self.situation_report.insert_message(self.message_about_drone)


    def select_message_about_drone(self):
        """Chose message to show if intruder presses 'd' for drone"""
        messages_list = ['Your drone was sold by your commander to the enemy.',
                        'Your drone has not reached the battlefield.',
                        "You sold parts of the drone, now it's missing the camera.",
                        'Your drone has been handed over to a private military group.',
                        "You've never had a drone.",
                        'Your general took the drone to his villa by the sea.',
                        "I don't understand, what are these 'drones'?",
                        "Your general's son is now playing with a drone at home.",
                        'Yesterday the military command promised that the drones will reach you tomorrow.',
                        "What do you mean by 'drone'?",
                        'Drone is in the air, but lost control and video.',
                        'The drone failed to launch.',
                        'The drone took off successfully and crashed.',
                        'Yesterday you stepped on the wing of the drone.',
                        "The drone's batteries are dead.",
                        "You used drone's fuel to warm you up on a cold night."]
        selected_message = random.choice(messages_list)
        return selected_message

    def make_turn(self):
        """Player fires shots from artillery guns and receives the same in return from computer, after shots checks for active units, if not - end battle"""

        # Make copy of last parameters to be able reset them on console to initial
        player_units_copy = self.shot_parameter_input.make_copy_of_units()
        # Find roles and units of the player and computer
        if Settings.player_role == "Defender":
            player_units = self.units["Defender"]
            computer_units = self.units["Intruder"]
        else:
            player_units = self.units["Intruder"]
            computer_units = self.units["Defender"]
        
        # Lists for blast coordinates of player and computer used to draw on map and radar
        blasts_list_player = [] 
        blasts_list_computer = []
        self.turn_index += 1 # Calculate turns (attacks)
        self.situation_report.insert_message(f"      ----- ----- ATTACK #{self.turn_index} ----- -----")
    
        # Show in situation report latest shot parameters
        self.shot_parameter_input.show_previous(player_units_copy)

        def get_active_units(units):
            """Return a list of active units."""
            active_units = []
            for unit in units:
                # 1 in 30 chance that the unit is broken if it's an Intruder unit
                if unit.player_role == "Intruder" and unit.unit_type == "artillery" and random.randint(1, 30) == 7:
                    unit.is_active = False
                    if Settings.player_role == "Defender":
                        self.situation_report.insert_message(f"Unit {unit.name} Nr.{unit.unit_number} is silent.")
                    else:
                        self.situation_report.insert_message(f"Unit {unit.name} Nr.{unit.unit_number} is broken.")
                    # Set related ammo unit to False
                    for related_unit in self.all_units_list:
                        if (related_unit.unit_number == unit.unit_number and 
                            related_unit.unit_type == 'ammo' and 
                            related_unit.player_role == unit.player_role):
                            related_unit.is_active = False
                if unit.is_active:
                    active_units.append(unit)
            return active_units
        # Get active player units
        self.active_player_units = get_active_units(player_units)
        assert len(self.active_player_units) % 2 == 0

        # Calculate trajectories of player's shots
        for unit in self.active_player_units:
            if unit.unit_type == "artillery":
                x_start, y_start = unit.coords
                p_charge = unit.charge
                elevation = unit.elevation
                azimuth = unit.azimuth
                map_direction = self.map_direction
                wind_speed = self.weather_conditions["Wind Speed,(m/s)"]
                wind_gust = self.weather_conditions["Wind Gust,(m/s)"]
                wind_direction = self.weather_conditions["Wind Direction,(°)"]
                blast_position_player = self.shot.calculate_shot_end_position(x_start, y_start, p_charge, elevation, azimuth, map_direction, wind_speed, wind_gust, wind_direction)
                # Intruders shots are less accurate
                if Settings.player_role == "Intruder":
                    blast_position_player = (blast_position_player[0] + random.randint(-100, 100), blast_position_player[1] + random.randint(-100, 100))
                # Inform player about the shot
                self.situation_report.insert_message(f"Unit {unit.name} Nr. {unit.unit_number} fired!")
                shot_sound_length = random.uniform(0.3, self.sound_manager.sounds['shot'].get_length())
                self.sound_manager.play_sound('shot', delay=shot_sound_length)
                # Add blast coordinates to the list
                if Settings.player_role == "Intruder" and random.randint(1, 30) == 7:
                    # 1 in 30 chance that the shell will not explode if it's an Intruder shell
                    self.situation_report.insert_message("The shell did not explode.")
                else:
                    blasts_list_player.append(blast_position_player)
                # Subtract ammo shot made
                related_units_found = 0
                for related_unit in self.active_player_units:
                    if (related_unit.unit_number == unit.unit_number and related_unit.unit_type == 'ammo'):
                        related_unit.ammo.set(related_unit.ammo.get() - 1)
                        related_units_found += 1
                # Assert that exactly one related unit was found
                assert related_units_found == 1, f"Unexpected number of related units found: {related_units_found}"
        
        # Computer makes decision which units to target
        def select_random_units(active_units, num_units):
            """Return a list of random units from the list of active units."""
            return random.sample(active_units, num_units)

        def computer_make_decision(player_units, computer_units):
            """Have the AI make a decision on which units to target."""
            
            # Get active computer units
            active_computer_units = get_active_units(computer_units)

            # Intruder does not have drone, therefore does not see ammo units
            if Settings.player_role == "Defender":
                self.active_player_units = [unit for unit in self.active_player_units if unit.unit_type == 'artillery']

            if self.active_player_units and active_computer_units:

                # Decide how many units to target based on the number of active computer units
                num_targets = min(len(active_computer_units), len(self.active_player_units))

                # Select the targets
                self.target_units = select_random_units(self.active_player_units, num_targets)
                return self.target_units
            else:
                return []

        def computer_fire_shot(unit):
            """Computer fires shot at player's unit position"""
            
            # First three shots of intruder shall be less accurate
            if self.turn_index - 1 <= 2:
                first_shots_correction = Settings.first_shots_accuracy[self.turn_index - 1]
            else:
                first_shots_correction = 0
            if Settings.player_role == "Defender":
                return (round(unit.coords[0] + random.randint(-300 - first_shots_correction, 300 + first_shots_correction)), round(unit.coords[1] + random.randint(-300 - first_shots_correction , 300 + first_shots_correction)))
            else:
                return (round(unit.coords[0] + random.randint(-150, 150)), round(unit.coords[1] + random.randint(-150, 150)))

        # Computer chooses target units for the first time
        if not self.target_units:
            self.target_units = computer_make_decision(player_units, computer_units)

        # Computer checks if in targets are disabled units
        for unit in self.target_units:
            if not unit.is_active:
                self.target_units = computer_make_decision(player_units, computer_units)

        # Computer fires shots at target units coords
        # Make the sound of incoming shell
        self.sound_manager.play_sound('incoming', delay=2)
        target_index = 0
        active_computer_artillery = [unit for unit in computer_units if unit.is_active and unit.unit_type == 'artillery']
        blast_count = 0
        for shooter in active_computer_artillery:
            # Check if the current target is still active
            while self.target_units and not self.target_units[target_index % len(self.target_units)].is_active:
                # If not, find a new target and update target_index
                self.target_units = computer_make_decision(player_units, computer_units)
                if not self.target_units: # break the loop if no active target units found
                    self.show_battle_results()
                target_index = 0

            if self.target_units: # if there are active target units
                # Make the shot
                blast_position_computer = computer_fire_shot(self.target_units[target_index])
                # Calculate blast number
                if Settings.player_role == "Defender" and random.randint(1, 30) == 7:
                    # 1 in 30 chance that the shell will not explode if it's an Intruder shell
                    self.situation_report.insert_message("A shell fell nearby but did not explode.")
                else:
                    blast_count += 1
                    # Inform player about blast with sound
                    if blast_count == 1:
                        blast_sound_length = 1
                    else:
                        blast_sound_length = random.uniform(0.3, self.sound_manager.sounds['blast'].get_length())
                    self.sound_manager.play_sound('blast', delay=blast_sound_length)
                    # Add blast coordinates to the list
                    blasts_list_computer.append(blast_position_computer)
                if len(self.target_units) > 1:  # Check if there are still targets left
                    target_index = (target_index + 1) % len(self.target_units)
                # Subtract ammo shot made
                for related_unit in computer_units:
                    if related_unit.unit_number == shooter.unit_number and related_unit.unit_type == 'ammo':
                        related_unit.ammo.set(related_unit.ammo.get() - 1)
            else: # if no active target units, shooter units stop firing
                self.show_battle_results()
        # Inform player about blasts
        self.situation_report.insert_message(f"{blast_count} enemy blasts counted")

        # Draw blasts pits on the map and blasts echo arcs on radar
        for index, blasts_list in enumerate((blasts_list_player, blasts_list_computer)):    
            for coords in blasts_list:
                if Settings.player_role == "Defender":
                    self.map_drone.add_blast_pit(coords)
                self.radar.add_blast_echo(index, coords)
        
        # Loop through all units for damage and loss of ammo
        blasts_list = blasts_list_player + blasts_list_computer
        for unit in self.all_units_list:
            # Loop through all blasts
            for blast_coords in blasts_list:
                # Calculate damage or ammo loss
                loss = self.shot.calculate_damage_or_ammo_loss(unit, blast_coords)
                if unit.unit_type == 'artillery':
                    # Add damage to unit's health
                    unit.damage.set(min(unit.damage.get() + loss, 100))
                    if loss > 0:
                        self.situation_report.insert_message(f"{unit.name} Nr.{unit.unit_number} got {loss} damage")
                        # Sound of damage
                        destroy_sound_length = random.uniform(0.3, self.sound_manager.sounds['destroy'].get_length())
                        self.sound_manager.play_sound('destroy', delay=destroy_sound_length)
                    if unit.damage.get() >= 50 and unit.is_active:
                        # If the unit's damage is more than or equal to 50, make it and related unit inactive
                        self.situation_report.insert_message(f"{unit.name} Nr.{unit.unit_number} was destroyed")
                        unit.is_active = False
                        for related_unit in self.all_units_list:
                            if (related_unit.unit_number == unit.unit_number and 
                                related_unit.unit_type == 'ammo' and 
                                related_unit.player_role == unit.player_role):
                                related_unit.is_active = False
                elif unit.unit_type == 'ammo':
                    # Subtract ammo loss from unit's ammo
                    unit.ammo.set(max(unit.ammo.get() - loss, 0))
                    if loss > 0:
                        self.situation_report.insert_message(f"{unit.name} Nr.{unit.unit_number} was damaged")
                        # Sound of damage
                        destroy_sound_length = random.uniform(0.3, self.sound_manager.sounds['destroy'].get_length())
                        self.sound_manager.play_sound('destroy', delay=destroy_sound_length)
                    if unit.ammo.get() <= 0 and unit.is_active:
                        # If the unit's ammo is less than or equal to 0, make it and related unit inactive
                        self.situation_report.insert_message(f"{unit.name} Nr.{unit.unit_number} is empty")
                        unit.is_active = False
                        for related_unit in self.all_units_list:
                            if (related_unit.unit_number == unit.unit_number and 
                                related_unit.unit_type == 'artillery' and 
                                related_unit.player_role == unit.player_role):
                                related_unit.is_active = False
                                self.situation_report.insert_message(f"{related_unit.name} Nr.{related_unit.unit_number} was silenced")

        # Get active units
        active_player_units = get_active_units(player_units)
        active_computer_units = get_active_units(computer_units)
        if active_player_units and active_computer_units:
            pass
        else:
            self.show_battle_results()

    def show_battle_results(self):
        """Shows statistics of the round"""

        def continue_execution():
            """Function created to make 3 sec pause before the console changes after message in situation report will be read"""

            # Close war statistics, raise main window
            self.main.border_frame.pack_forget()
            self.raise_menu()

            # Disable console 'fire' button
            self.shot_parameter_input.buttons['FIRE'].config(state='disabled')
            self.shot_parameter_input.buttons['CONFIRM'].config(state='disabled')
            self.shot_parameter_input.buttons['RESET'].config(state='disabled')

            # Collect statistics to variable
            battle_statistics = f"\n                                   BATTLE REPORT Nr.{Settings.battle_index}\n\n"

            # Set the sequence how the information is displayed, player's stats goes first
            sequence = ["Defender", "Intruder"] if Settings.player_role == "Defender" else ["Intruder", "Defender"]

            # Dictionary to hold statistics for each role
            role_statistics = [f"\n          {Settings.call_sign}, Your stats:\n", f"\n\n          Enemy's stats:\n"]

            for index, role in enumerate(sequence):
                # Collect stats for each unit type
                stats = {"units_labels": ["         "], "damages": [], "status_artillery": [], "status_ammo": [], "ammos": []}

                for unit in self.units[role]:
                    if unit.unit_type == "artillery":
                        stats["units_labels"].append(f"UNIT {unit.unit_number}")
                        stats["damages"].append(f"{unit.damage.get()}")
                        stats["status_artillery"].append(f"{unit.is_active}")
                    elif unit.unit_type == "ammo":
                        stats["ammos"].append(f"{unit.ammo.get()}")
                        stats["status_ammo"].append(f"{unit.is_active}")

                # Prepare the report message
                length = 35 - int(len(self.units[role]) * 3 / 2)  # Center table
                spaces = " " * length
                report_message = "\n"
                report_message += f"{spaces}" + " ".join(f"{unit_label:>7}" for unit_label in stats["units_labels"]) + "\n"
                report_message += f"{spaces}" + "DAMAGE:   " + " ".join(f"{damage:>7}" for damage in stats["damages"]) + "\n"
                report_message += f"{spaces}" + "HOWITZER: " + " ".join(f"{status.replace('True', 'Active').replace('False', 'Down') :>7}" for status in stats["status_artillery"]) + "\n"
                report_message += f"{spaces}" + "AMMO:     " + " ".join(f"{ammo:>7}" for ammo in stats["ammos"]) + "\n"
                report_message += f"{spaces}" + "TRUCK:    " + " ".join(f"{status.replace('True', 'Active').replace('False', 'Down') :>7}" for status in stats["status_ammo"]) + "\n"

                # Add report message to role statistics
                role_statistics[index] += report_message

            # Finalize collection of the statistics to variable
            battle_statistics += ''.join(role_statistics[:2])
            battle_statistics += self.battle_message

            # Create a temporary file and write the statistics to it
            with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as temp_file:
                temp_file.write(battle_statistics)
            txt_file_name = temp_file.name

            # Show battle statistics in root window console
            self.main.display_txt_file(txt_file_name)

            # Remove temporary file
            os.remove(txt_file_name)

        # Set game status to 'show battle results', used in main window
        Settings.battle_results = True

        # Check who won the battle
        self.calculate_battle_results()

        # Raise console for 4 sec.
        self.raise_console()
        self.console.console.after(4000, continue_execution)

    def update_war_results(self, event):
        """Shows updated war statistics window"""
        
        # Unbind keyboard keys for navigation among console, drone and radar
        self.main.root.unbind_all('e')
        self.main.root.unbind_all('d')
        self.main.root.unbind_all('r')
        self.main.root.unbind_all('c')
        self.main.root.unbind_all('s')
        self.main.root.unbind_all('w')
        
        # Remove battle number from root
        self.battle_no_label.place_forget()

        # Close war statistics, raise main window, destroy windows of the round
        self.main.root.attributes('-topmost', 1)
        if Settings.player_role != 'Intruder':
            self.map_drone.map_window.destroy()
        self.radar.radar_window.destroy()
        self.console.console.destroy()

        self.setup.calculate_remainder_add() # Return what's left after battle to the equipment and ammo total amounts
        
        # Set game status to 'show war results', used in main window
        Settings.war_results = True
        self.main.border_frame.pack_forget()
        self.show_war_results()

    def show_war_results(self):
        """Shows game general statistics"""

        # Change game status, used in main window
        Settings.battle_results = False

        # Collect statistics to variable
        war_statistics = "\n                                       WAR REPORT\n\n"

        # Set the sequence how the information is displayed, player's stats goes first
        sequence = ["Defender", "Intruder"] if Settings.player_role == "Defender" else ["Intruder", "Defender"]

        spaces = " " * 33 # Add indent

        # Prepare statistics
        statistics = {}

        # Defenders statistics
        statistics["Defender"] = [
            f"Units left total:     {self.setup.defender_total_units}\n",
            f"Ammo left total:      {self.setup.defender_total_ammo}\n",
            f"Damage left total:    {self.setup.defender_total_damage}\n\n",
                            ]
        # Intruders statistics
        statistics["Intruder"] = [
            f"Units left total:     {self.setup.intruder_total_units}\n",
            f"Ammo left total:      {self.setup.intruder_total_ammo}\n",
            f"Damage left total:    {self.setup.intruder_total_damage}\n\n",
                            ]
        # Dictionary headlines for each player
        role_headlines = [f"\n          {Settings.call_sign}, Your stats:\n\n", f"\n          Enemy's stats:\n\n"]

        report_message = ""
        for index, role in enumerate(sequence):
            # Merge players statistics to one string
            report_message += role_headlines[index]
            for line in statistics[role]:
                report_message += spaces + line

        # Summary statistics
        battles_fought = f"\n          Total battles fought:          {Settings.battle_index}\n"
        battles_won = f"          Battles won:                   {Settings.battles_won}\n"
        battles_lost = f"          Battles lost:                  {Settings.battles_lost}\n"
        battles_tied = f"          Tied battles:                  {Settings.battles_tied}\n"
        territory = f"          Total territory occupied:      {Settings.territory_occupied}\n"
        if Settings.end_war_results:
            final_message = f"\n YOUR WAR IS OVER: {self.final_message}\n"
            Settings.game = False
        else:
            final_message = ""

        # Finalize collection of the statistics to variable
        war_statistics += report_message + battles_fought + battles_won + battles_lost + battles_tied + territory + final_message

        # Create a temporary file and write the statistics to it
        with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as temp_file:
            temp_file.write(war_statistics)
        txt_file_name = temp_file.name
        # Show war statistics in root window console
        self.main.display_txt_file(txt_file_name)

        # Remove temporary file
        os.remove(txt_file_name)

    def calculate_battle_results(self):
        """Check who wins the battle"""
        
        def get_active_units(units):
            """Return a list of active units."""
            return [unit for unit in units if unit.is_active]

        # Find roles and units of the player and computer
        if Settings.player_role == "Defender":
            player_units = self.units["Defender"]
            computer_units = self.units["Intruder"]
        else:
            player_units = self.units["Intruder"]
            computer_units = self.units["Defender"]

        # Get active units
        active_player_units = get_active_units(player_units)
        active_computer_units = get_active_units(computer_units)

        # Set default battle message
        self.battle_message = ""
        spaces = " " * 10

        if len(active_player_units) == 0 and len(active_computer_units) == 0:
            # Battle ends in a draw
            self.battle_message = f"\n\n{spaces}We retreat from the battlefield.\n" + f"{spaces}The enemy retreated from the battlefield."
            Settings.battles_tied += 1
        elif len(active_player_units) > 0 and len(active_computer_units) == 0:
            # Player wins
            if Settings.player_role == "Defender":
                Settings.territory_occupied -= 2  # Player reoccupies 2% of the territory
            else:
                Settings.territory_occupied += 2  # Player occupies 2% of the territory
            self.battle_message = f"\n\n{spaces}{Settings.call_sign}, you won the battle and took 2% of the territory.\n" + f"{spaces}Now the occupied territory is {Settings.territory_occupied}%."
            Settings.battles_won += 1
        elif len(active_player_units) == 0 and len(active_computer_units) > 0:
            # Player loses
            if Settings.player_role == "Intruder":
                Settings.territory_occupied -= 2  # Player loses 2% of the territory
            else:
                Settings.territory_occupied += 2  # Player takes 2% of the territory
            self.battle_message = f"\n\n{spaces}{Settings.call_sign}, you lost the battle and 2% of the territory.\n" + f"{spaces}Now the occupied territory is {Settings.territory_occupied}%."
            Settings.battles_lost += 1
        else:
            self.situation_report.insert_message(f"\n\nThe battle is ongoing. Current percentage of occupied territory is {Settings.territory_occupied}%.\n")

        # Remove the first 10 spaces before inserting into situation report
        stripped_battle_message = self.battle_message[10:]
        self.situation_report.insert_message("\n" + stripped_battle_message)


    def show_war_end_results(self, defender_total_damage, intruder_total_damage):
        """Prepares game end message for war statistics"""

        # Set variables for the final message
        self.final_message = ""
        player_role = Settings.player_role
        call_sign = Settings.call_sign

        # Change game status to add final message to war results window
        Settings.war_results = False
        Settings.end_war_results = True
        Settings.game = False
        self.main.root.unbind_all('c')

        # Consequences of breaching the front line
        if intruder_total_damage < 150 and defender_total_damage >= 50:
            Settings.territory_occupied -= 10
            if player_role == "Defender":
                self.final_message += "Your relentless artillery fire has dealt significant damage, disrupting the enemy front line and triggering a disorganized retreat. This successful operation has led to the liberation of 10% of the Homeland.\n"
            elif player_role == "Intruder":
                self.final_message += "The damage dealt by the defenders has been catastrophic, leading to a collapse of your front line. In the chaotic retreat, your forces have abandoned 10% of the occupied territory in a single day.\n"
        elif defender_total_damage < 50 and intruder_total_damage >=150:
            Settings.territory_occupied += 10
            if player_role == "Defender":
                self.final_message += "The heavy damage inflicted by the invaders has forced your units to retreat deeper into your country. This strategic fallback, albeit necessary, results in the loss of an additional 10% of your territory.\n"
            elif player_role == "Intruder":
                self.final_message += "Your devastating artillery fire has dealt substantial damage to the defenders. Their front line crumbles, and as they retreat, you seize an additional 10% of their territory.\n"

        territory_occupied = Settings.territory_occupied

        if player_role == "Defender":
            if 0 < territory_occupied < 20:
                self.final_message += (f"{call_sign}, you fought hard but wisely. You managed to halt the "
                                      f"invaders and reclaim {20 - territory_occupied}% of your homeland. New battles await "
                                      f"you in the future.")
            elif territory_occupied > 20:
                self.final_message += (f"{call_sign}, you fought valiantly, yet the enemy was strong. You managed to slow "
                                      f"their advance, but the aggressor has penetrated {territory_occupied - 20}% further "
                                      f"into your homeland. The struggle for survival continues.")
            elif territory_occupied == 20:
                self.final_message += (f"{call_sign}, you fought with bravery and selflessness. You were able to halt the "
                                      f"superior enemy force, yet the aggressor still occupies 20% of the homeland. The "
                                      f"fight for liberation continues.")
            elif territory_occupied <= 0:
                self.final_message += (f"{call_sign}, you have won the war and freed your homeland from the invaders. The "
                                      f"cost was high... Long live the homeland! Long live the heroes!")

        elif player_role == "Intruder":
            if 0 < territory_occupied < 20:
                self.final_message += (f"{call_sign}, you acted aggressively and confidently, yet your cause was misguided. "
                                      f"As a result, you suffered many defeats and relinquished {20 - territory_occupied}% "
                                      f"of the occupied territory. The repercussions of your actions are becoming increasingly apparent.")
            elif territory_occupied > 20:
                self.final_message += (f"{call_sign}, your aggressive tactics and disregard for losses allowed you to occupy "
                                      f"an additional {territory_occupied - 20}% of territory. This type of warfare brings "
                                      f"only death and irreversible harm to the world.")
            elif territory_occupied == 20:
                self.final_message += (f"{call_sign}, despite your superior resources and aggressive tactics, you were "
                                      f"halted by intelligent and patriotic defenders. Their will to defend their homeland "
                                      f"is stronger than your weapons.")
            elif territory_occupied <= 0:
                self.final_message += (f"{call_sign}, you lost your unjust and unprovoked war against a country of strong spirit. "
                                      f"Your own nation is in turmoil, and you and your accomplices now face justice at The Hague.")
        self.main.border_frame.pack_forget()
        self.show_war_results()
