"""One battle: the turn-by-turn exchange of fire between the player and the computer."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from artillery_war.config import (
    DEFENDER,
    DESTROYED_DAMAGE,
    FAILURE_ODDS,
    FAILURE_ROLL,
    FIRST_SHOTS_ACCURACY,
    INTRUDER,
    MAX_DAMAGE,
    TERRITORY_PER_BATTLE,
)
from artillery_war.core.ballistics import Ballistics
from artillery_war.core.events import BattleOver, Blasts, Event, Message, Sound
from artillery_war.core.units import Coords, Unit, partner

if TYPE_CHECKING:
    from artillery_war.config import GameOptions
    from artillery_war.core.campaign import WarRecord, Weather

# One ballistics model for every battle: all maps share the same scale.
BALLISTICS = Ballistics()


@dataclass(frozen=True)
class FiringOrder:
    """The player's settings for one gun."""

    azimuth: float
    elevation: float
    charge: int


# Outcomes of a battle, from the player's point of view.
WON, LOST, TIED, ONGOING = 'won', 'lost', 'tied', 'ongoing'


class Battle:
    """State and rules of a single battle.

    A turn has two calls: ``begin_turn`` (numbers the attack) and
    ``resolve_turn`` (both sides fire, blasts are applied). Both return a list of
    events for the interface to show. All randomness comes from ``rng``, and the
    order of draws is part of the recorded game behavior.
    """

    def __init__(
        self,
        options: GameOptions,
        record: WarRecord,
        rng: random.Random,
        units: dict[str, list[Unit]],
        weather: Weather,
        map_direction: int,
        map_path: Path,
        radar_path: Path,
        map_size: tuple[int, int],
    ) -> None:
        self.options = options
        self.record = record  # WarRecord, updated when the battle ends
        self.rng = rng
        self.units = units
        self.all_units = units[DEFENDER] + units[INTRUDER]
        self.weather = weather
        self.map_direction = map_direction
        self.map_path = map_path
        self.radar_path = radar_path
        self.map_size = map_size
        self.turn_index = 0
        self.target_units: list[Unit] = []  # the computer keeps its targets between turns
        self.active_player_units: list[Unit] = []
        self.outcome: str | None = None
        self.battle_message = ''
        self._events: list[Event] = []

    @property
    def player_role(self) -> str:
        return self.options.player_role

    @property
    def player_units(self) -> list[Unit]:
        return self.units[self.player_role]

    @property
    def computer_units(self) -> list[Unit]:
        return self.units[self.options.computer_role]

    @property
    def is_over(self) -> bool:
        return self.outcome is not None

    # ------------------------------------------------------------------ helpers

    def _say(self, text: str) -> None:
        self._events.append(Message(text))

    def _sound(self, name: str, delay: float | None = None, random_delay: bool = False) -> None:
        self._events.append(Sound(name, delay=delay, spread=self.rng.random() if random_delay else None))

    def _failure(self) -> bool:
        """The 1-in-30 roll used for intruder breakdowns and duds."""
        return self.rng.randint(1, FAILURE_ODDS) == FAILURE_ROLL

    def _take_out_of_action(self, unit: Unit) -> Unit | None:
        unit.is_active = False
        other = partner(unit, self.all_units)
        if other is not None:
            other.is_active = False
        return other

    def _active_units(self, units: list[Unit]) -> list[Unit]:
        """Active units of a side, after rolling for intruder gun breakdowns.

        Every intruder gun is rolled for, even one already out of action.
        """
        active = []
        for unit in units:
            if unit.player_role == INTRUDER and unit.is_artillery and self._failure():
                unit.is_active = False
                word = 'silent' if self.player_role == DEFENDER else 'broken'
                self._say(f'Unit {unit.name} Nr.{unit.unit_number} is {word}.')
                truck = partner(unit, self.all_units)
                if truck is not None:
                    truck.is_active = False
            if unit.is_active:
                active.append(unit)
        return active

    # --------------------------------------------------------------------- turn

    def begin_turn(self) -> list[Event]:
        """Number the next attack; returns its header line."""
        if self.is_over:
            return []
        self._events = []
        self.turn_index += 1
        self._say(f'      ----- ----- ATTACK #{self.turn_index} ----- -----')
        return self._flush()

    def resolve_turn(self, orders: dict[int, FiringOrder]) -> list[Event]:
        """Fire the player's guns with ``orders`` ({unit_number: FiringOrder}), answer with the computer's."""
        if self.is_over:
            return []
        self._events = []
        blasts_player: list[Coords] = []
        blasts_computer: list[Coords] = []

        self.active_player_units = self._active_units(self.player_units)
        assert len(self.active_player_units) % 2 == 0, 'every active gun must have an active truck'

        self._fire_player_guns(orders, blasts_player)
        self._fire_computer_guns(blasts_computer)
        self._events.append(Blasts(list(blasts_player), list(blasts_computer)))
        self._apply_blasts(blasts_player + blasts_computer)

        active_player_units = self._active_units(self.player_units)
        active_computer_units = self._active_units(self.computer_units)
        if not (active_player_units and active_computer_units):
            self._conclude()
        return self._flush()

    def _fire_player_guns(self, orders: dict[int, FiringOrder], blasts: list[Coords]) -> None:
        w = self.weather
        for unit in self.active_player_units:
            if not unit.is_artillery:
                continue
            order = orders[unit.unit_number]
            x, y = BALLISTICS.shot_end_position(
                unit.coords[0],
                unit.coords[1],
                order.charge,
                order.elevation,
                order.azimuth,
                self.map_direction,
                w.wind_speed,
                w.wind_gust,
                w.wind_direction,
            )
            if self.player_role == INTRUDER:
                # Intruder shells are less accurate.
                x += self.rng.randint(-100, 100)
                y += self.rng.randint(-100, 100)
            self._say(f'Unit {unit.name} Nr. {unit.unit_number} fired!')
            self._sound('shot', random_delay=True)
            if self.player_role == INTRUDER and self._failure():
                self._say('The shell did not explode.')
            else:
                blasts.append((x, y))

            trucks = [u for u in self.active_player_units if u.unit_number == unit.unit_number and u.is_ammo]
            assert len(trucks) == 1, f'Unexpected number of related units found: {len(trucks)}'
            trucks[0].ammo -= 1

    def _choose_targets(self) -> list[Unit]:
        """Pick player units to aim at: one per active computer unit, at most one each."""
        active_computer_units = self._active_units(self.computer_units)
        if self.player_role == DEFENDER:
            # The intruder has no drone, so it only sees the defender's guns (on radar), not the trucks.
            self.active_player_units = [u for u in self.active_player_units if u.is_artillery]
        if self.active_player_units and active_computer_units:
            num_targets = min(len(active_computer_units), len(self.active_player_units))
            self.target_units = self.rng.sample(self.active_player_units, num_targets)
            return self.target_units
        return []

    def _aim_at(self, unit: Unit) -> Coords:
        """Landing point of a computer shell aimed at ``unit``."""
        if self.player_role == DEFENDER:
            # The computer intruder's first three volleys are less accurate.
            spread = 300 + (FIRST_SHOTS_ACCURACY[self.turn_index - 1] if self.turn_index - 1 <= 2 else 0)
        else:
            spread = 150
        return (
            round(unit.coords[0] + self.rng.randint(-spread, spread)),
            round(unit.coords[1] + self.rng.randint(-spread, spread)),
        )

    def _fire_computer_guns(self, blasts: list[Coords]) -> None:
        if not self.target_units:
            self.target_units = self._choose_targets()

        # Re-plan once for every target lost since the last turn.
        for unit in list(self.target_units):
            if not unit.is_active:
                self.target_units = self._choose_targets()

        self._sound('incoming', delay=2)
        target_index = 0
        shooters = [u for u in self.computer_units if u.is_active and u.is_artillery]
        blast_count = 0
        for shooter in shooters:
            while self.target_units and not self.target_units[target_index % len(self.target_units)].is_active:
                self.target_units = self._choose_targets()
                target_index = 0

            if not self.target_units:
                # Nothing left to shoot at. The battle is decided once, at the end of the turn,
                # after this turn's blasts have been applied.
                continue

            landing = self._aim_at(self.target_units[target_index])
            if self.player_role == DEFENDER and self._failure():
                self._say('A shell fell nearby but did not explode.')
            else:
                blast_count += 1
                if blast_count == 1:
                    self._sound('blast', delay=1)
                else:
                    self._sound('blast', random_delay=True)
                blasts.append(landing)
            if len(self.target_units) > 1:
                target_index = (target_index + 1) % len(self.target_units)
            for truck in self.computer_units:
                if truck.unit_number == shooter.unit_number and truck.is_ammo:
                    truck.ammo -= 1
        self._say(f'{blast_count} enemy blasts counted')

    def _apply_blasts(self, blasts: list[Coords]) -> None:
        for unit in self.all_units:
            for blast in blasts:
                loss = BALLISTICS.blast_effect(unit, blast)
                if unit.is_artillery:
                    unit.damage = min(unit.damage + loss, MAX_DAMAGE)
                    if loss > 0:
                        self._say(f'{unit.name} Nr.{unit.unit_number} got {loss} damage')
                        self._sound('destroy', random_delay=True)
                    if unit.damage >= DESTROYED_DAMAGE and unit.is_active:
                        self._say(f'{unit.name} Nr.{unit.unit_number} was destroyed')
                        self._take_out_of_action(unit)
                else:
                    unit.ammo = max(unit.ammo - loss, 0)
                    if loss > 0:
                        self._say(f'{unit.name} Nr.{unit.unit_number} was damaged')
                        self._sound('destroy', random_delay=True)
                    if unit.ammo <= 0 and unit.is_active:
                        self._say(f'{unit.name} Nr.{unit.unit_number} is empty')
                        gun = self._take_out_of_action(unit)
                        if gun is not None:
                            self._say(f'{gun.name} Nr.{gun.unit_number} was silenced')

    # ------------------------------------------------------------------ ending

    def withdraw(self) -> list[Event]:
        """The player retreats: all their units leave the battlefield."""
        if self.is_over:
            return []
        self._events = []
        for unit in self.player_units:
            unit.is_active = False
        self._conclude()
        return self._flush()

    def _conclude(self) -> None:
        """Decide the battle and update the war record."""
        player_active = any(u.is_active for u in self.player_units)
        computer_active = any(u.is_active for u in self.computer_units)
        record = self.record
        spaces = ' ' * 10
        self.battle_message = ''
        call_sign = self.options.call_sign

        if not player_active and not computer_active:
            self.outcome = TIED
            self.battle_message = (
                f'\n\n{spaces}We retreat from the battlefield.\n{spaces}The enemy retreated from the battlefield.'
            )
            record.battles_tied += 1
        elif player_active and not computer_active:
            self.outcome = WON
            record.territory_occupied += -TERRITORY_PER_BATTLE if self.player_role == DEFENDER else TERRITORY_PER_BATTLE
            self.battle_message = (
                f'\n\n{spaces}{call_sign}, you won the battle and took 2% of the territory.\n'
                f'{spaces}Now the occupied territory is {record.territory_occupied}%.'
            )
            record.battles_won += 1
        elif not player_active and computer_active:
            self.outcome = LOST
            record.territory_occupied += -TERRITORY_PER_BATTLE if self.player_role == INTRUDER else TERRITORY_PER_BATTLE
            self.battle_message = (
                f'\n\n{spaces}{call_sign}, you lost the battle and 2% of the territory.\n'
                f'{spaces}Now the occupied territory is {record.territory_occupied}%.'
            )
            record.battles_lost += 1
        else:
            self.outcome = ONGOING
            self._say(
                f'\n\nThe battle is ongoing. Current percentage of occupied territory is {record.territory_occupied}%.\n'  # noqa: E501
            )

        # The report line is the battle message without its first 10 characters.
        self._say('\n' + self.battle_message[10:])
        self._events.append(BattleOver())

    def _flush(self) -> list[Event]:
        events, self._events = self._events, []
        return events
