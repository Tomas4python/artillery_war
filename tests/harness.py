"""Headless drivers for the game core, used by the characterization scenarios.

``HeadlessWar`` plays complete wars the way the interface does (begin turn,
enter firing orders, resolve turn, absorb remains, next battle) with a scripted
player. The player's inputs come from a private RNG so they never disturb the
game's own random sequence.
"""

import math
import random

from artillery_war import paths
from artillery_war.config import DEFENDER, INTRUDER
from artillery_war.core.battle import BALLISTICS, FiringOrder
from artillery_war.core.campaign import Campaign
from artillery_war.core.events import BattleOver, Blasts, Message


def unit_state(unit):
    state = {
        'role': unit.player_role,
        'type': unit.unit_type,
        'number': unit.unit_number,
        'name': unit.name,
        'coords': list(unit.coords),
        'direction': unit.image_direction,
        'orientation': unit.unit_orientation,
        'active': unit.is_active,
    }
    if unit.is_artillery:
        state['damage'] = unit.damage
    else:
        state['ammo'] = unit.ammo
    return state


def units_state(units):
    return [unit_state(u) for u in units[DEFENDER] + units[INTRUDER]]


def record_counters(record):
    return {
        'territory_occupied': record.territory_occupied,
        'battle_index': record.battle_index,
        'battles_won': record.battles_won,
        'battles_lost': record.battles_lost,
        'battles_tied': record.battles_tied,
    }


def campaign_totals(campaign):
    return {
        name: getattr(campaign, name)
        for name in (
            'defender_total_units',
            'intruder_total_units',
            'defender_total_ammo',
            'intruder_total_ammo',
            'defender_total_damage',
            'intruder_total_damage',
        )
    }


class HeadlessWar:
    MAX_TURNS = 40
    MAX_BATTLES = 60

    def __init__(self, options, game_seed, aim_seed, skilled=False):
        self.options = options
        self.campaign = Campaign(options, random.Random(game_seed))
        self.aim_rng = random.Random(aim_seed)
        self.skilled = skilled
        self.last_battle_message = None

    # ------------------------------------------------------------ the player

    def _orders(self, battle):
        targets = [u for u in battle.computer_units if u.is_artillery and u.is_active]
        orders = {}
        guns = [u for u in battle.player_units if u.is_artillery]
        for index, unit in enumerate(guns):
            if self.skilled and targets:
                azimuth, elevation, charge = self._firing_solution(battle, unit, targets[index % len(targets)].coords)
                azimuth += self.aim_rng.uniform(-0.3, 0.3)
                elevation += self.aim_rng.uniform(-0.3, 0.3)
            else:
                azimuth = self.aim_rng.uniform(-60, 60)
                elevation = self.aim_rng.uniform(15, 75)
                charge = self.aim_rng.randint(1, 5)
            orders[unit.unit_number] = FiringOrder(round(azimuth, 1), round(min(max(elevation, 15.0), 75.0), 1), charge)
        return orders

    @staticmethod
    def _firing_solution(battle, unit, target):
        """Aim like a competent player: solve the no-wind ballistics, then correct for wind."""
        w = battle.weather
        aim_point = target
        azimuth = elevation = 0.0
        charge = 5
        for _ in range(4):
            dx = aim_point[0] - unit.coords[0]
            dy = unit.coords[1] - aim_point[1]
            distance = math.hypot(dx, dy) * BALLISTICS.scale
            bearing = math.degrees(math.atan2(dx, dy))
            azimuth = (bearing - battle.map_direction) % 360
            max_range = 5000.0
            for charge in range(1, 6):
                max_range = (5000 * charge) / math.sin(math.radians(90))
                if distance <= max_range * 0.95:
                    break
            ratio = min(distance / max_range, 1.0)
            elevation = 90 - math.degrees(math.asin(ratio)) / 2  # high-angle solution
            end = BALLISTICS.shot_end_position(
                unit.coords[0],
                unit.coords[1],
                charge,
                elevation,
                azimuth,
                battle.map_direction,
                w.wind_speed,
                w.wind_gust,
                w.wind_direction,
            )
            aim_point = (aim_point[0] - (end[0] - target[0]), aim_point[1] - (end[1] - target[1]))
        return azimuth, elevation, charge

    # ------------------------------------------------------------- the game

    def run_battle(self):
        battle = self.campaign.new_battle()
        record = {
            'map': paths.asset_key(battle.map_path),
            'radar': paths.asset_key(battle.radar_path),
            'map_direction': battle.map_direction,
            'weather': battle.weather.as_report(),
            'units_initial': units_state(battle.units),
            'turns': [],
        }
        battle_over_events = 0
        while battle_over_events == 0 and battle.turn_index < self.MAX_TURNS:
            events = battle.begin_turn()
            events += battle.resolve_turn(self._orders(battle))
            battle_over_events += sum(isinstance(e, BattleOver) for e in events)
            echoes = []
            for e in events:
                if isinstance(e, Blasts):
                    echoes += [(0, c) for c in e.player] + [(1, c) for c in e.computer]
            record['turns'].append(
                {
                    'echoes': echoes,
                    'messages': [e.text for e in events if isinstance(e, Message)],
                    'battle_results_calls': battle_over_events,
                    'units': [[u.damage if u.is_artillery else u.ammo, u.is_active] for u in battle.all_units],
                }
            )
        record['units_final'] = units_state(battle.units)
        if battle.is_over:
            self.last_battle_message = battle.battle_message
        record['battle_message'] = self.last_battle_message
        record['counters_after'] = record_counters(self.campaign.record)
        return record

    def run_war(self):
        campaign = self.campaign
        war: dict[str, object] = {'initial_totals': campaign_totals(campaign), 'battles': []}
        while not campaign.should_end() and campaign.record.battle_index < self.MAX_BATTLES:
            battle = self.run_battle()
            campaign.absorb_battle_remains()
            battle['totals_after'] = campaign_totals(campaign)
            war['battles'].append(battle)  # type: ignore[attr-defined]
        war['final_message'] = campaign.finish()
        war['final_counters'] = record_counters(campaign.record)
        return war
