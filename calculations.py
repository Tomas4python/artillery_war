import random
import math

from settings import Settings


class Shot:
    """A class for calculating shot trajectory, damage to artillery units and loss of ammo"""

    def __init__(self):
        """ Initialize variables for calculations."""

        self.field_height = Settings.field_height

        # Constants
        self.g = 9.8 # Acceleration due to gravity in m/s^2
        self.scale = round(25000 / self.field_height, 3) # Scale 25 km in m/pixel

    def calculate_shot_end_position(self, x_start, y_start, p_charge, elevation, azimuth, map_direction, wind_speed, wind_gust, wind_direction):
       
        # Adjust the azimuth and wind direction according to the map_direction
        azimuth = round((map_direction + float(azimuth.get())) % 360, 1)
        wind_direction = round((map_direction + wind_direction) % 360, 1)
        wind_speed = wind_speed + (wind_gust - wind_speed) / 2

        # Convert degrees to radians
        elevation_rad = math.radians(float(elevation.get()))
        azimuth_rad = math.radians(azimuth)
        wind_direction_rad = math.radians(wind_direction)

        # Calculate initial velocity based on a standard charge (e.g., charge 1)
        # This velocity is calculated using the range equation (R = v^2 / g * sin(2*theta))
        # where R = 5 km (for charge 1), theta = 45 degrees
        v_1 = math.sqrt(5 * 1000 * self.g / math.sin(math.radians(2 * 45)))

        # Adjust the initial velocity based on the actual charge
        v = v_1 * math.sqrt(int(p_charge.get()))

        # Calculate the total distance traveled by the projectile in the absence of wind
        d = (v**2 / self.g) * math.sin(2 * elevation_rad)

        # Adjust the distance for wind speed and direction
        # This is a simplified model that assumes the wind has a constant effect over the entire trajectory
        wind_effect = wind_speed * math.cos(wind_direction_rad - azimuth_rad) # Component of wind in the direction of fire
        d_adjusted = d + wind_effect * d / v

        # Calculate the change in x and y position
        dx = d_adjusted * math.sin(azimuth_rad) / self.scale
        dy = d_adjusted * math.cos(azimuth_rad) / self.scale

        # Calculate the end position
        x_end = round(x_start + dx)
        y_end = round(y_start - dy)

        return (x_end, y_end)

    def calculate_damage_or_ammo_loss(self, unit, blast_coords):
        """Calculate damage to artillery unit and ammo loss if shell landed nearby unit"""

        # Calculate the distance between the unit and the blast
        x1, y1 = unit.coords
        x2, y2 = blast_coords
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        # Calculate the damage or ammo loss
        if unit.unit_type == 'artillery':
            if distance <= 100:
                return int(100 - distance)  # Damage from 1 to 100
            else:
                return 0  # No damage
        elif unit.unit_type == 'ammo':
            if distance <= 100:
                return int(10 - distance / 10) # Loss of from 1 to 10 ammo
            else:
                return 0  # No loss

