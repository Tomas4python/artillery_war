"""Compass directions on the rotated battlefield map.

Each battle's map is rotated: true north lies ``map_direction`` degrees clockwise
from the top of the screen (the radar's compass shows it, and the shells follow
it: see ``Ballistics.shot_end_position``). Screen offsets must therefore be
turned back by ``map_direction`` before they are named.
"""

from __future__ import annotations

import math

POINTS = ('North', 'North-East', 'East', 'South-East', 'South', 'South-West', 'West', 'North-West')


def true_bearing(screen_dx: float, screen_dy: float, map_direction: float) -> float:
    """Compass bearing (0 = north, clockwise) of a screen offset; screen y grows downwards."""
    screen_bearing = math.degrees(math.atan2(screen_dx, -screen_dy))  # clockwise from the top of the screen
    return (screen_bearing - map_direction) % 360


def compass_point(screen_dx: float, screen_dy: float, map_direction: float) -> str:
    """Nearest of the eight compass points, e.g. 'South-West'."""
    bearing = true_bearing(screen_dx, screen_dy, map_direction)
    return POINTS[int((bearing + 22.5) % 360 // 45)]
