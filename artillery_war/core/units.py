"""Battlefield units and their deployment on the map."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass

from artillery_war.config import DEFENDER, INTRUDER, UNIT_AMMO

Coords = tuple[int, int]  # map pixels

ARTILLERY = 'artillery'
AMMO = 'ammo'

ARTILLERY_NAMES = {DEFENDER: 'M777', INTRUDER: '2A65'}
TRUCK_NAMES = {DEFENDER: ('TATRA', 'MAN', 'SISU'), INTRUDER: ('KAMAZ', 'URAL', 'GAZ', 'ZIL')}


@dataclass(eq=False)
class Unit:
    """An artillery gun or its ammunition truck.

    Each gun is paired with one truck: they share ``unit_number`` and
    ``player_role``. When one of the pair goes out of action, so does the other.
    """

    unit_number: int
    unit_type: str  # ARTILLERY or AMMO
    coords: Coords
    image_direction: str  # 'north' or 'south', the way the sprite faces
    player_role: str  # DEFENDER or INTRUDER
    unit_orientation: float  # extra sprite rotation, turns trucks towards their gun
    name: str
    damage: int = 0  # artillery only, percent
    ammo: int = UNIT_AMMO  # ammo only, shells left
    is_active: bool = True

    @property
    def is_artillery(self) -> bool:
        return self.unit_type == ARTILLERY

    @property
    def is_ammo(self) -> bool:
        return self.unit_type == AMMO


def make_unit(
    rng: random.Random,
    unit_number: int,
    unit_type: str,
    coords: Coords,
    image_direction: str,
    player_role: str,
    unit_orientation: float,
) -> Unit:
    """Create a unit; trucks get a random model name (this draws from ``rng``)."""
    if unit_type == ARTILLERY:
        name = ARTILLERY_NAMES[player_role]
    else:
        name = rng.choice(TRUCK_NAMES[player_role])
    return Unit(unit_number, unit_type, coords, image_direction, player_role, unit_orientation, name)


def dist(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def partner(unit: Unit, units: Iterable[Unit]) -> Unit | None:
    """The truck of a gun, or the gun of a truck."""
    wanted = AMMO if unit.is_artillery else ARTILLERY
    for other in units:
        if (
            other.unit_number == unit.unit_number
            and other.unit_type == wanted
            and other.player_role == unit.player_role
        ):
            return other
    return None


def generate_units(
    rng: random.Random,
    player_role: str,
    map_size: tuple[int, int],
    units_to_generate_defender: int,
    units_to_generate_intruder: int,
    deployment: str,
) -> dict[str, list[Unit]]:
    """Place both sides' units for one battle.

    The player always deploys in the bottom (southern) half of the map and the
    computer in the top half. Defender guns are placed individually; intruder
    guns come in groups of three, in a line ('inline') or scattered ('random').

    Returns ``{'Defender': [...], 'Intruder': [...]}`` with each gun followed by its truck.
    """
    units: dict[str, list[Unit]] = {DEFENDER: [], INTRUDER: []}

    player_is_defender = player_role == DEFENDER
    half_map_size = (map_size[0], map_size[1] // 2)
    defenders_part_of_map = (
        (half_map_size[1] + 1000, map_size[1] - 250) if player_is_defender else (250, half_map_size[1] - 1000)
    )
    intruders_part_of_map = (
        (350, half_map_size[1] - 1000) if player_is_defender else (half_map_size[1] + 1000, map_size[1] - 350)
    )
    # Trucks stand behind their gun, i.e. further from the enemy.
    defenders_ammo_position = (150, 200) if player_is_defender else (-200, -150)
    intruders_ammo_position = (-150, -50) if player_is_defender else (50, 150)
    defenders_unit_direction = 'north' if player_is_defender else 'south'
    intruders_unit_direction = 'south' if player_is_defender else 'north'

    # Defender: guns at least 300 px from any other defender unit.
    defender_unit_positions: list[Coords] = []
    for i in range(units_to_generate_defender):
        while True:
            x = rng.randint(250, half_map_size[0] - 250)
            y = rng.randint(*defenders_part_of_map)
            if not any(dist((x, y), pos) < 300 for pos in defender_unit_positions):
                defender_unit_positions.append((x, y))
                units[DEFENDER].append(make_unit(rng, i + 1, ARTILLERY, (x, y), defenders_unit_direction, DEFENDER, 1))
                break

        ammo_x = x + rng.randint(-200, 200)
        ammo_y = y + rng.randint(*defenders_ammo_position)
        defender_unit_positions.append((ammo_x, ammo_y))
        unit_orientation = (x - ammo_x) / -3
        units[DEFENDER].append(
            make_unit(rng, i + 1, AMMO, (ammo_x, ammo_y), defenders_unit_direction, DEFENDER, unit_orientation)
        )

    # Intruder: groups of three guns, group centers at least 500 px apart.
    intruder_unit_positions: list[Coords] = []  # used by 'random' deployment only
    intruder_groups: list[Coords] = []
    i = 0
    for _ in range(units_to_generate_intruder // 3):
        while True:
            group_center = (rng.randint(350, half_map_size[0] - 350), rng.randint(*intruders_part_of_map))
            if not any(dist(group_center, center) < 500 for center in intruder_groups):
                intruder_groups.append(group_center)
                break

        if deployment == 'inline':
            # Old doctrine: the three guns stand in a line.
            line_angle = rng.randint(-50, 50)
            line_length = rng.randint(150, 200)
            for position in (-1, 0, 1):
                x = group_center[0] + line_length * position
                y = group_center[1] + line_angle * position
                i += 1
                units[INTRUDER].append(make_unit(rng, i, ARTILLERY, (x, y), intruders_unit_direction, INTRUDER, 1))

                ammo_x = x + rng.randint(-100, 100)
                ammo_y = y + rng.randint(*intruders_ammo_position)
                unit_orientation = (x - ammo_x) / 2
                units[INTRUDER].append(
                    make_unit(rng, i, AMMO, (ammo_x, ammo_y), intruders_unit_direction, INTRUDER, unit_orientation)
                )
        else:
            # New doctrine: guns scattered around the group center, at least 150 px apart.
            for _ in range(3):
                while True:
                    x = group_center[0] + rng.randint(-300, 300)
                    y = group_center[1] + rng.randint(-300, 300)
                    if not any(dist((x, y), pos) < 150 for pos in intruder_unit_positions):
                        i += 1
                        intruder_unit_positions.append((x, y))
                        units[INTRUDER].append(
                            make_unit(rng, i, ARTILLERY, (x, y), intruders_unit_direction, INTRUDER, 1)
                        )
                        break

                ammo_x = x + rng.randint(-150, 150)
                ammo_y = y + rng.randint(*intruders_ammo_position)
                intruder_unit_positions.append((ammo_x, ammo_y))
                unit_orientation = (x - ammo_x) / 2
                units[INTRUDER].append(
                    make_unit(rng, i, AMMO, (ammo_x, ammo_y), intruders_unit_direction, INTRUDER, unit_orientation)
                )

    return units
