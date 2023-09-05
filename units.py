import tkinter as tk
import math
import random

from settings import Settings

class Unit:
    """Class for unit creation"""
    
    def __init__(self, unit_number, unit_type, coords, image_direction, player_role, unit_orientation, azimuth=None, elevation=None, charge=None):
        self.unit_number = unit_number
        self.unit_type = unit_type  # 'artillery' or 'ammo'
        self.player_role = player_role # 'Defender' or 'Intruder'
        self.coords = coords  # a tuple (x, y)
        self.unit_orientation = unit_orientation # use to orient ammo unit to artillery unit
        self.image_direction = image_direction  # a string indicating the direction

        # Define unit-specific attributes
        if self.unit_type == 'artillery':
            self.name = 'M777' if self.player_role == 'Defender' else '2A65'
            self.damage = tk.IntVar(value=0)  # damage is initially 0
            self.elevation = tk.StringVar(value=elevation)
            self.azimuth = tk.StringVar(value=azimuth)
            self.charge = tk.StringVar(value=charge)
            self.is_active = True
        elif self.unit_type == 'ammo':
            # Define truck names lists for defender and intruder
            defender_names = ['TATRA', 'MAN', 'SISU']
            intruder_names = ['KAMAZ', 'URAL', 'GAZ', 'ZIL']

            # Select a random name based on player role
            self.name = random.choice(defender_names) if self.player_role == 'Defender' else random.choice(intruder_names)
            self.ammo = tk.IntVar(value=10)  # ammo is initially 10
            self.is_active = True

def dist(p1, p2):
    # Calculate Euclidean distance between two points
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def generate_units(player_role, map_size, units_to_generate_defender, units_to_generate_intruder):
    """Generate units for the round of the game"""

    # Create dict for all units
    units = { 'Defender': [], 'Intruder': []}

    # Define top and bottom map zones and unit directions for defender and intruder based on the player's role (player always bottom, computer - top)
    half_map_size = (map_size[0], map_size[1] // 2)
    defenders_part_of_map = (half_map_size[1] + 1000, map_size[1] - 250) if player_role == 'Defender' else (250, half_map_size[1] - 1000)
    intruders_part_of_map = (350, half_map_size[1] - 1000) if player_role == 'Defender' else (half_map_size[1] + 1000, map_size[1] - 350)
    defenders_ammo_position = (150, 200) if player_role == 'Defender' else (-200, -150)
    intruders_ammo_position = (-150, -50) if player_role == 'Defender' else (50, 150)
    defenders_unit_direction = 'north' if player_role == 'Defender' else 'south'
    intruders_unit_direction = 'south' if player_role == 'Defender' else 'north'

    # Generate defender units with unit positions and directions
    defender_unit_positions = []

    for i in range(units_to_generate_defender):
        while True:
            x = random.randint(250, half_map_size[0] - 250)
            y = random.randint(*defenders_part_of_map)
            if not any(dist((x, y), pos) < 300 for pos in defender_unit_positions):
                defender_unit_positions.append((x, y))
                # Create artillery unit and add to dictionary
                units['Defender'].append(Unit(i + 1, 'artillery', (x, y), defenders_unit_direction,'Defender', 1))
                break

        # Generate Ammo unit position behind the Artillery unit
        ammo_x = x + random.randint(-200, 200)
        ammo_y = y + random.randint(*defenders_ammo_position)
        defender_unit_positions.append((ammo_x, ammo_y))
        # Orient the ammo unit direction to artillery unit position
        unit_orientation = (x - ammo_x) / -3
        # Create ammo unit and add to dictionary
        units['Defender'].append(Unit(i + 1, 'ammo', (ammo_x, ammo_y), defenders_unit_direction, 'Defender', unit_orientation))

    # Generate intruder units with unit positions an directions 
    intruder_unit_positions = [] # If random unit deployment will be chosen
    intruder_groups = [] # Intruders units are grouped of 3

    i = 0 # Index for intruder unit number
    for _ in range(units_to_generate_intruder // 3):
        while True:
            group_center = (random.randint(350, half_map_size[0] - 350), 
                            random.randint(*intruders_part_of_map))
            if not any(dist(group_center, center) < 500 for center in intruder_groups):
                intruder_groups.append(group_center)
                break
        if Settings.deployment == 'inline':
            # Deploy the units inline as old doctrine requires
            position_in_line = [-1, 0, 1]
            line_angle = random.randint(-50, 50)
            line_lenght = random.randint(150, 200)
            for position in position_in_line:
                x = group_center[0] + line_lenght * position
                y = group_center[1] + line_angle * position
                i += 1
                # Create artillery unit and add to dictionary
                units['Intruder'].append(Unit(i, 'artillery', (x, y), intruders_unit_direction, 'Intruder', 1))
                
                # Generate Ammo unit position behind the Artillery unit
                ammo_x = x + random.randint(-100, 100)
                ammo_y = y + random.randint(*intruders_ammo_position)
                # Orient the ammo unit direction to artillery unit position
                unit_orientation = (x - ammo_x) / 2
                # Create ammo unit and add to dictionary
                units['Intruder'].append(Unit(i, 'ammo', (ammo_x, ammo_y), intruders_unit_direction, 'Intruder', unit_orientation))
        else:
            # Random unit deployment as new doctrine requires
            for _ in range(3):
                while True:
                    x = group_center[0] + random.randint(-300, 300)
                    y = group_center[1] + random.randint(-300, 300)
                    if not any(dist((x, y), pos) < 150 for pos in intruder_unit_positions):
                        i += 1
                        intruder_unit_positions.append((x, y))
                        # Create artillery unit and add to dictionary
                        units['Intruder'].append(Unit(i, 'artillery', (x, y), intruders_unit_direction, 'Intruder', 1))
                        break

                # Generate Ammo unit position behind the Artillery unit
                ammo_x = x + random.randint(-150, 150)
                ammo_y = y + random.randint(*intruders_ammo_position)
                intruder_unit_positions.append((ammo_x, ammo_y))
                # Orient the ammo unit direction to artillery unit position
                unit_orientation = (x - ammo_x) / 2
                # Create ammo unit and add to dictionary
                units['Intruder'].append(Unit(i, 'ammo', (ammo_x, ammo_y), intruders_unit_direction, 'Intruder', unit_orientation))

    return units
