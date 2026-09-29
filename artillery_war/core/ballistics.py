"""Shell trajectory and blast effect calculations."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from artillery_war.config import BATTLEFIELD_LENGTH_M, SCALE_REFERENCE_HEIGHT_PX

if TYPE_CHECKING:
    from artillery_war.core.units import Coords, Unit

GRAVITY = 9.8  # m/s^2
BLAST_RADIUS_PX = 100


class Ballistics:
    """Where a shell lands and what its blast does to nearby units."""

    def __init__(self, field_height: int = SCALE_REFERENCE_HEIGHT_PX) -> None:
        # Meters per map pixel.
        self.scale = round(BATTLEFIELD_LENGTH_M / field_height, 3)
        # Muzzle velocity for charge 1, chosen so that charge 1 fired at 45° reaches 5 km:
        # range R = v^2 / g * sin(2 * theta).
        self.charge_1_velocity = math.sqrt(5 * 1000 * GRAVITY / math.sin(math.radians(2 * 45)))

    def shot_end_position(
        self,
        x_start: float,
        y_start: float,
        charge: int | str,
        elevation: float | str,
        azimuth: float | str,
        map_direction: float,
        wind_speed: float,
        wind_gust: float,
        wind_direction: float,
    ) -> Coords:
        """Landing point, in map pixels, of a shell fired from (x_start, y_start).

        ``azimuth`` and ``wind_direction`` are relative to the map, which is rotated
        by ``map_direction`` degrees. Wind uses the midpoint of speed and gust and
        is modeled as a constant push along the line of fire.
        """
        azimuth = round((map_direction + float(azimuth)) % 360, 1)
        wind_direction = round((map_direction + wind_direction) % 360, 1)
        wind_speed = wind_speed + (wind_gust - wind_speed) / 2

        elevation_rad = math.radians(float(elevation))
        azimuth_rad = math.radians(azimuth)
        wind_direction_rad = math.radians(wind_direction)

        v = self.charge_1_velocity * math.sqrt(int(charge))

        # Distance traveled without wind, then corrected by the wind component along the line of fire.
        d = (v**2 / GRAVITY) * math.sin(2 * elevation_rad)
        wind_effect = wind_speed * math.cos(wind_direction_rad - azimuth_rad)
        d_adjusted = d + wind_effect * d / v

        dx = d_adjusted * math.sin(azimuth_rad) / self.scale
        dy = d_adjusted * math.cos(azimuth_rad) / self.scale

        return round(x_start + dx), round(y_start - dy)

    @staticmethod
    def blast_effect(unit: Unit, blast_coords: Coords) -> int:
        """Damage (artillery, 0-100) or lost shells (ammo, 0-10) caused by a blast."""
        x1, y1 = unit.coords
        x2, y2 = blast_coords
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if distance > BLAST_RADIUS_PX:
            return 0
        if unit.is_artillery:
            return int(100 - distance)
        return int(10 - distance / 10)
