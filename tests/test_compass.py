"""The out-of-range direction names must agree with the ballistics and the radar compass."""

import math

import pytest

from artillery_war.core.ballistics import Ballistics
from artillery_war.core.compass import compass_point, true_bearing

AIMS = [(0, 'North'), (45, 'North-East'), (90, 'East'), (135, 'South-East'), (180, 'South'),
        (225, 'South-West'), (270, 'West'), (315, 'North-West')]  # fmt: skip
MAP_DIRECTIONS = [0, 17, 90, 133, 180, 246, 270, 359]


@pytest.mark.parametrize('map_direction', MAP_DIRECTIONS)
@pytest.mark.parametrize(('azimuth', 'name'), AIMS)
def test_shell_fired_on_an_azimuth_is_named_after_it(map_direction, azimuth, name):
    """A shell fired at azimuth 90 lands East of the gun, whatever the map rotation."""
    x0, y0 = 2000, 6000
    x, y = Ballistics().shot_end_position(x0, y0, 5, 45, azimuth, map_direction, 0.0, 0.0, 0.0)
    assert compass_point(x - x0, y - y0, map_direction) == name


@pytest.mark.parametrize('map_direction', MAP_DIRECTIONS)
def test_radar_compass_north_marker_is_bearing_zero(map_direction):
    """The radar draws 'N' at Tk angle 360 - map_direction + 90 (counter-clockwise from 3 o'clock)."""
    angle = math.radians(360 - map_direction + 90)
    dx, dy = math.cos(angle), -math.sin(angle)  # Tk angles go counter-clockwise; screen y grows downwards
    bearing = true_bearing(dx, dy, map_direction)
    assert min(bearing, 360 - bearing) == pytest.approx(0, abs=1e-9)


def test_unrotated_map_names_screen_edges():
    assert compass_point(0, -1, 0) == 'North'  # top
    assert compass_point(1, 0, 0) == 'East'  # right
    assert compass_point(0, 1, 0) == 'South'  # bottom
    assert compass_point(-1, 0, 0) == 'West'  # left (the old message called this 'East')


def test_map_turned_upside_down_swaps_top_and_bottom():
    assert compass_point(0, -1, 180) == 'South'
    assert compass_point(0, 1, 180) == 'North'
