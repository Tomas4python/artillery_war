"""The war: resources carried between battles, battle setup and the final verdict."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from artillery_war import paths
from artillery_war.config import (
    DEFENDER,
    DESTROYED_DAMAGE,
    END_THRESHOLDS,
    INITIAL_TERRITORY_OCCUPIED,
    INTRUDER,
    INTRUDER_THRESHOLD_MULTIPLIER,
    ROUND_AMOUNTS,
    TERRITORY_FRONT_BREACH,
    TOTAL_AMOUNTS,
    UNIT_AMMO,
    GameOptions,
)
from artillery_war.core.battle import Battle
from artillery_war.core.units import generate_units


@dataclass
class Weather:
    """Conditions for one battle; only the wind affects the shells."""

    pressure: float  # hPa
    humidity: float  # %
    temperature: float  # °C
    wind_speed: float  # m/s
    wind_gust: float  # m/s
    wind_direction: float  # degrees, relative to the map

    def as_report(self) -> dict[str, float]:
        """Weather as the labeled rows shown on the console."""
        return {
            'Sea Level Pressure,(hPa)': self.pressure,
            'Relative Humidity,(%)': self.humidity,
            'Air Temperature, (°C)': self.temperature,
            'Wind Speed,(m/s)': self.wind_speed,
            'Wind Gust,(m/s)': self.wind_gust,
            'Wind Direction,(°)': self.wind_direction,
        }


def generate_weather(rng: random.Random) -> Weather:
    """Random weather; the gust is 1 to half the wind speed above it."""
    pressure = round(rng.uniform(990, 1030), 1)
    humidity = round(rng.uniform(20, 100), 1)
    temperature = round(rng.uniform(-5, 35), 1)
    wind_speed = round(rng.uniform(2, 30), 1)
    wind_direction = round(rng.uniform(0, 360), 1)
    wind_gust = round(wind_speed + rng.uniform(1, int(wind_speed / 2)), 1)
    return Weather(pressure, humidity, temperature, wind_speed, wind_gust, wind_direction)


@dataclass
class WarRecord:
    """Score of the war so far."""

    territory_occupied: int = INITIAL_TERRITORY_OCCUPIED
    battle_index: int = 0
    battles_won: int = 0
    battles_lost: int = 0
    battles_tied: int = 0


_map_sizes: dict[Path, tuple[int, int]] = {}


def _map_size(path: Path) -> tuple[int, int]:
    if path not in _map_sizes:
        with Image.open(path) as img:
            _map_sizes[path] = img.size
    return _map_sizes[path]


class Campaign:
    """One war, from the first battle until a side runs out of resources.

    The intruder always has three times the defender's resources, but loses more
    of them between battles (see ``absorb_battle_remains``).
    """

    def __init__(self, options: GameOptions, rng: random.Random) -> None:
        self.options = options
        self.rng = rng
        self.record = WarRecord()
        level = options.level

        self.defender_total_units, self.intruder_total_units = TOTAL_AMOUNTS[level]['units']
        self.defender_total_ammo, self.intruder_total_ammo = TOTAL_AMOUNTS[level]['ammo']
        self.defender_total_damage, self.intruder_total_damage = TOTAL_AMOUNTS[level]['damage']

        self.defender_round_units, self.intruder_round_units = ROUND_AMOUNTS[level]['units']
        self.defender_round_ammo, self.intruder_round_ammo = ROUND_AMOUNTS[level]['ammo']
        self.defender_round_damage, self.intruder_round_damage = ROUND_AMOUNTS[level]['damage']

        self.used_maps: list[tuple[Path, Path]] = []
        self.units_to_generate_defender = 0  # guns deployed in the current battle
        self.units_to_generate_intruder = 0
        self.battle: Battle | None = None
        self.final_message = ''

    # ------------------------------------------------------------------ battles

    def new_battle(self) -> Battle:
        """Commit resources to the next battle and deploy the units."""
        level = self.options.level
        self.record.battle_index += 1

        # Guns to deploy, limited by the per-battle cap and by what is left (each gun needs 10 shells).
        self.units_to_generate_defender = min(
            ROUND_AMOUNTS[level]['units'][0],
            self.defender_total_units,
            ROUND_AMOUNTS[level]['ammo'][0] // UNIT_AMMO,
            self.defender_total_ammo // UNIT_AMMO,
        )
        self.units_to_generate_intruder = min(
            ROUND_AMOUNTS[level]['units'][1],
            self.intruder_total_units,
            ROUND_AMOUNTS[level]['ammo'][1] // UNIT_AMMO,
            self.intruder_total_ammo // UNIT_AMMO,
        )
        self._subtract_committed_resources()

        map_path, radar_path = self._choose_map()
        map_size = _map_size(map_path)
        map_direction = self.rng.randint(0, 360)
        units = generate_units(
            self.rng,
            self.options.player_role,
            map_size,
            self.units_to_generate_defender,
            self.units_to_generate_intruder,
            self.options.deployment,
        )
        weather = generate_weather(self.rng)

        self.battle = Battle(
            self.options, self.record, self.rng, units, weather, map_direction, map_path, radar_path, map_size
        )
        return self.battle

    def _choose_map(self) -> tuple[Path, Path]:
        """A random map not used yet in this cycle; the cycle restarts once all were used."""
        maps = paths.map_images()
        if len(self.used_maps) == len(maps):
            self.used_maps = []
        choice = self.rng.choice([m for m in maps if m not in self.used_maps])
        self.used_maps.append(choice)
        return choice

    def _subtract_committed_resources(self) -> None:
        # Note the intruder's unit count is multiplied by 3 here, although it is already a gun count;
        # the per-battle cap (min) keeps the result in range. Kept as-is: it is part of the balance.
        self.defender_total_units -= min(
            self.units_to_generate_defender, self.defender_total_units, self.defender_round_units
        )
        self.defender_total_ammo -= min(
            int(self.units_to_generate_defender * UNIT_AMMO), self.defender_total_ammo, self.defender_round_ammo
        )
        self.intruder_total_units -= min(
            self.units_to_generate_intruder * 3, self.intruder_total_units, self.intruder_round_units
        )
        self.intruder_total_ammo -= min(
            int(self.units_to_generate_intruder * 3 * UNIT_AMMO), self.intruder_total_ammo, self.intruder_round_ammo
        )

    def absorb_battle_remains(self) -> None:
        """Return what survived the last battle to the war totals, and book its damage.

        Defender guns come back if they are under 50% damage; only half of the
        intruder's surviving units come back, and only active trucks keep their shells.
        """
        assert self.battle is not None, 'no battle has been fought yet'
        defender_units = self.battle.units[DEFENDER]
        intruder_units = self.battle.units[INTRUDER]
        self.defender_total_units += len([u for u in defender_units if u.is_artillery and u.damage < DESTROYED_DAMAGE])
        self.defender_total_ammo += sum(u.ammo for u in defender_units if u.is_ammo)
        self.defender_total_damage -= sum(u.damage for u in defender_units if u.is_artillery)
        self.intruder_total_units += len([u for u in intruder_units if u.is_active]) // 2
        self.intruder_total_ammo += sum(u.ammo for u in intruder_units if u.is_ammo and u.is_active)
        self.intruder_total_damage -= sum(u.damage for u in intruder_units if u.is_artillery)

    def should_end(self) -> bool:
        """True when either side lacks the units, ammo or damage capacity for another battle."""
        units_threshold, ammo_threshold, damage_threshold = END_THRESHOLDS[self.options.level]
        if (
            self.defender_total_units < units_threshold
            or self.defender_total_ammo < ammo_threshold
            or self.defender_total_damage < damage_threshold
        ):
            return True
        m = INTRUDER_THRESHOLD_MULTIPLIER
        return (
            self.intruder_total_units < units_threshold * m
            or self.intruder_total_ammo < ammo_threshold * m
            or self.intruder_total_damage < damage_threshold * m
        )

    def finish(self) -> str:
        """Apply the end-of-war territory change and compose the final message."""
        self.record.territory_occupied, self.final_message = final_war_verdict(
            self.options.player_role,
            self.options.call_sign,
            self.record.territory_occupied,
            self.defender_total_damage,
            self.intruder_total_damage,
        )
        return self.final_message


def final_war_verdict(
    player_role: str,
    call_sign: str,
    territory_occupied: int,
    defender_total_damage: int,
    intruder_total_damage: int,
) -> tuple[int, str]:
    """Return (territory after the front-line check, final message)."""
    message = ''

    # A side with (almost) no damage capacity left loses its front line.
    if intruder_total_damage < 150 and defender_total_damage >= 50:
        territory_occupied -= TERRITORY_FRONT_BREACH
        if player_role == DEFENDER:
            message += 'Your relentless artillery fire has dealt significant damage, disrupting the enemy front line and triggering a disorganized retreat. This successful operation has led to the liberation of 10% of the Homeland.\n'  # noqa: E501
        elif player_role == INTRUDER:
            message += 'The damage dealt by the defenders has been catastrophic, leading to a collapse of your front line. In the chaotic retreat, your forces have abandoned 10% of the occupied territory in a single day.\n'  # noqa: E501
    elif defender_total_damage < 50 and intruder_total_damage >= 150:
        territory_occupied += TERRITORY_FRONT_BREACH
        if player_role == DEFENDER:
            message += 'The heavy damage inflicted by the invaders has forced your units to retreat deeper into your country. This strategic fallback, albeit necessary, results in the loss of an additional 10% of your territory.\n'  # noqa: E501
        elif player_role == INTRUDER:
            message += 'Your devastating artillery fire has dealt substantial damage to the defenders. Their front line crumbles, and as they retreat, you seize an additional 10% of their territory.\n'  # noqa: E501

    t = territory_occupied
    if player_role == DEFENDER:
        if 0 < t < 20:
            message += (
                f'{call_sign}, you fought hard but wisely. You managed to halt the '
                f'invaders and reclaim {20 - t}% of your homeland. New battles await '
                f'you in the future.'
            )
        elif t > 20:
            message += (
                f'{call_sign}, you fought valiantly, yet the enemy was strong. You managed to slow '
                f'their advance, but the aggressor has penetrated {t - 20}% further '
                f'into your homeland. The struggle for survival continues.'
            )
        elif t == 20:
            message += (
                f'{call_sign}, you fought with bravery and selflessness. You were able to halt the '
                f'superior enemy force, yet the aggressor still occupies 20% of the homeland. The '
                f'fight for liberation continues.'
            )
        elif t <= 0:
            message += (
                f'{call_sign}, you have won the war and freed your homeland from the invaders. The '
                f'cost was high... Long live the homeland! Long live the heroes!'
            )
    elif player_role == INTRUDER:
        if 0 < t < 20:
            message += (
                f'{call_sign}, you acted aggressively and confidently, yet your cause was misguided. '
                f'As a result, you suffered many defeats and relinquished {20 - t}% '
                f'of the occupied territory. The repercussions of your actions are becoming increasingly apparent.'
            )
        elif t > 20:
            message += (
                f'{call_sign}, your aggressive tactics and disregard for losses allowed you to occupy '
                f'an additional {t - 20}% of territory. This type of warfare brings '
                f'only death and irreversible harm to the world.'
            )
        elif t == 20:
            message += (
                f'{call_sign}, despite your superior resources and aggressive tactics, you were '
                f'halted by intelligent and patriotic defenders. Their will to defend their homeland '
                f'is stronger than your weapons.'
            )
        elif t <= 0:
            message += (
                f'{call_sign}, you lost your unjust and unprovoked war against a country of strong spirit. '
                f'Your own nation is in turmoil, and you and your accomplices now face justice at The Hague.'
            )
    return territory_occupied, message
