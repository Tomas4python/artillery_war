import random
import os
import tempfile
import glob
from PIL import Image
from settings import Settings
from units import  Unit, generate_units


class GameSetup:
    """Class for game and round setup when starts"""

    def __init__(self, play_instance_refference):
        """Setup the game"""

        self.play = play_instance_refference

        #  Setting variables for the entire game:
        #                           the player's role,
        #                           game difficulty,
        #                           total number of units
        #                           total amount of ammo
        #                           total amount of damage    
        self.player_role = Settings.player_role
        self.difficulty_level = Settings.level
        
        # Set initial state of the battles statistics
        Settings.territory_occupied = 20
        Settings.battle_index = 0
        Settings.battles_won = 0
        Settings.battles_lost = 0
        Settings.battles_tied = 0

        # Set the total number of units, amounts of ammo and damage based on the difficulty level
        self.total_amounts = Settings.total_amounts

        self.defender_total_units, self.intruder_total_units = self.total_amounts[self.difficulty_level]['units']
        self.defender_total_ammo, self.intruder_total_ammo = self.total_amounts[self.difficulty_level]['ammo']
        self.defender_total_damage, self.intruder_total_damage = self.total_amounts[self.difficulty_level]['damage']

        # Set max number of units, amounts of ammo and damage based on the difficulty level for the one game round (battle)
        self.round_amounts = Settings.round_amounts
        self.defender_round_units, self.intruder_round_units = self.round_amounts[self.difficulty_level]['units']
        self.defender_round_ammo, self.intruder_round_ammo = self.round_amounts[self.difficulty_level]['ammo']
        self.defender_round_damage, self.intruder_round_damage = self.round_amounts[self.difficulty_level]['damage']

        # Setting empty list for used maps in the round
        self.used_maps = []

    def round_setup(self):
        """Setting variables for one game round"""

        # Calculate how many units and ammo to generate based on total remainder
        self.units_to_generate_defender = min(self.round_amounts[self.difficulty_level]['units'][0], self.defender_total_units, self.round_amounts[self.difficulty_level]['ammo'][0] // 10, self.defender_total_ammo // 10)
        self.units_to_generate_intruder = min(self.round_amounts[self.difficulty_level]['units'][1], self.intruder_total_units, self.round_amounts[self.difficulty_level]['ammo'][1] // 10, self.intruder_total_ammo // 10)

        # Subtract resources needed for the round from total amounts
        self.calculate_remainder_subtract()

        # Choose the map and get dimensions
        map_path, radar_path = self.get_random_map_and_radar()

        # Open the image file
        with Image.open(map_path) as img:
            # Get dimensions
            map_size = img.size
            Settings.field_width, Settings.field_height = map_size

        # Generate random map direction
        map_direction = random.randint(0, 360)

        # Generate units
        self.units = generate_units(self.player_role, map_size, self.units_to_generate_defender, self.units_to_generate_intruder)

        # Generate weather conditions
        weather_conditions = self.generate_weather_conditions()

        return weather_conditions, self.units, map_path, radar_path, map_direction
        
    def generate_weather_conditions(self):
        """Weather conditions generator"""

        # Generate random weather conditions for the game
        self.weather_conditions = {
            "Sea Level Pressure,(hPa)": round(random.uniform(990, 1030), 1),
            "Relative Humidity,(%)": round(random.uniform(20, 100), 1),
            "Air Temperature, (°C)": round(random.uniform(-5, 35), 1),
            "Wind Speed,(m/s)": round(random.uniform(2, 30), 1),
            "Wind Gust,(m/s)": None,
            "Wind Direction,(°)": round(random.uniform(0, 360), 1)
        }
        self.weather_conditions["Wind Gust,(m/s)"] = round(self.weather_conditions["Wind Speed,(m/s)"] + random.uniform(1, int(self.weather_conditions["Wind Speed,(m/s)"]/2)), 1)

        return self.weather_conditions

    def get_random_map_and_radar(self):
        """Choses random images from list for map and radar"""

        # Get a list of all map files
        maps = glob.glob(os.path.join('images', 'maps', 'map*.jpg'))

        # If all maps have been used, clear the used_maps list
        if len(self.used_maps) == len(maps):
            self.used_maps = []

        # Choose a random map that hasn't been used yet
        map_path = random.choice([map for map in maps if map not in self.used_maps])

        # Add the chosen map to the used maps list
        self.used_maps.append(map_path)

        # Build the corresponding radar file path
        map_filename = os.path.basename(map_path)
        map_number = map_filename[3:-4]  # strip off 'map' and '.jpg'
        radar_path = os.path.join('images', 'maps', 'radar' + map_number + '.jpg')

        return map_path, radar_path

    def game_should_end(self):
        """Check if there are left resources to continue game"""

        end_thresholds = {'easy': (1, 10, 50), 'medium': (1, 10, 50), 'hard': (1, 10, 50)}

        # Get the thresholds for the current difficulty level
        units_threshold, ammo_threshold, damage_threshold = end_thresholds[self.difficulty_level]

        # Check the conditions for the defender
        if self.defender_total_units < units_threshold or \
            self.defender_total_ammo < ammo_threshold or \
            self.defender_total_damage < damage_threshold:
                return True

        # Check the conditions for the intruder
        if self.intruder_total_units < units_threshold * 3 or \
            self.intruder_total_ammo < ammo_threshold * 3 or \
            self.intruder_total_damage < damage_threshold * 3:
                return True

        # If none of the end conditions were met, the game should continue
        return False

    def calculate_remainder_subtract(self):
        """Subtracts resources needed for the round from total amounts"""

        self.defender_total_units -= min(self.units_to_generate_defender, self.defender_total_units, self.defender_round_units)
        self.defender_total_ammo -= min( int(self.units_to_generate_defender * 10), self.defender_total_ammo, self.defender_round_ammo)
        self.intruder_total_units -= min(self.units_to_generate_intruder * 3, self.intruder_total_units, self.intruder_round_units)
        self.intruder_total_ammo -= min(int(self.units_to_generate_intruder * 3 * 10),self.intruder_total_ammo, self.intruder_round_ammo)

    def calculate_remainder_add(self):
        """Adds to total amounts the remainder of the resources from the active units after the loss incurred during the battle round, some disadvantages for intruder"""
        defender_units = [unit for unit in self.units["Defender"]]
        intruder_units = [unit for unit in self.units["Intruder"]]
        self.defender_total_units += len([unit for unit in defender_units if unit.unit_type == "artillery" and unit.damage.get() < 50])
        self.defender_total_ammo += sum(unit.ammo.get() for unit in defender_units if unit.unit_type == "ammo")
        self.defender_total_damage -= sum(unit.damage.get() for unit in defender_units if unit.unit_type == "artillery")
        self.intruder_total_units += len([unit for unit in intruder_units if unit.is_active]) // 2
        self.intruder_total_ammo += sum(unit.ammo.get() for unit in intruder_units if unit.unit_type == "ammo" and unit.is_active)
        self.intruder_total_damage -= sum(unit.damage.get() for unit in intruder_units if unit.unit_type == "artillery")

