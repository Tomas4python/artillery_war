"""Characterization scenarios: each returns JSON-serializable output of the current game maths.

The recorded output lives in ``tests/golden/<scenario>.json`` and is the reference
the refactored code must reproduce exactly. Regenerate it only on purpose:

    python -m tests.golden_cases --update            # all scenarios
    python -m tests.golden_cases --update shots      # one scenario
"""

import itertools
import json
import random
import sys
from pathlib import Path

from artillery_war import paths
from artillery_war.config import GameOptions
from artillery_war.core.ballistics import Ballistics
from artillery_war.core.campaign import Campaign, final_war_verdict
from artillery_war.core.units import Unit, generate_units
from tests import harness

GOLDEN_DIR = Path(__file__).parent / 'golden'


def scenario_shots():
    """Shot end positions over a grid of inputs, using the scale the game actually uses."""
    shot = Ballistics()
    results = []
    for azimuth, elevation, charge, map_direction, wind_speed, wind_direction in itertools.product(
        ('-270.5', '0', '12.3', '90', '180', '359.9'),
        ('15', '30.5', '45', '60', '75'),
        ('1', '3', '5'),
        (0, 45, 200, 360),
        (2.0, 15.5, 30.0),
        (0.0, 90.0, 237.4),
    ):
        wind_gust = wind_speed + 4.2
        end = shot.shot_end_position(
            2000,
            6000,
            charge,
            elevation,
            azimuth,
            map_direction,
            wind_speed,
            wind_gust,
            wind_direction,
        )
        results.append([azimuth, elevation, charge, map_direction, wind_speed, wind_direction, list(end)])
    return {'scale': shot.scale, 'results': results}


def scenario_shot_scale_per_field_height():
    """Scale derived from each field height (documents the constructor formula)."""
    out = {}
    for height in (4096, 6000, 8192, 10000):
        out[str(height)] = Ballistics(height).scale
    return out


def scenario_damage():
    out = []
    for unit_type in ('artillery', 'ammo'):
        unit = Unit(1, unit_type, (1000, 1000), 'north', 'Defender', 1, 'test')
        for dx, dy in itertools.product(range(0, 121, 7), range(0, 121, 11)):
            out.append([unit_type, dx, dy, Ballistics.blast_effect(unit, (1000 + dx, 1000 - dy))])
    return out


def scenario_generate_units():
    out = []
    for seed, role, deployment, (n_def, n_int) in itertools.product(
        (1, 2, 3),
        ('Defender', 'Intruder'),
        ('inline', 'random'),
        ((1, 3), (3, 9), (6, 18)),
    ):
        units = generate_units(random.Random(seed), role, (4407, 8192), n_def, n_int, deployment)
        out.append(
            {
                'seed': seed,
                'role': role,
                'deployment': deployment,
                'counts': [n_def, n_int],
                'units': harness.units_state(units),
            }
        )
    return out


def scenario_game_setup():
    """Resource bookkeeping: init totals, round sizing, map rotation, weather, end check."""
    out = []
    for level, role in itertools.product(('easy', 'medium', 'hard'), ('Defender', 'Intruder')):
        setup = Campaign(GameOptions(level=level, player_role=role, deployment='inline'), random.Random(42))
        rounds = []
        for _ in range(12):
            battle = setup.new_battle()
            units = battle.units
            # Simulate losses so calculate_remainder_add has something to count.
            for i, unit in enumerate(units['Defender'] + units['Intruder']):
                if unit.is_artillery:
                    unit.damage = (i * 17) % 101
                else:
                    unit.ammo = (i * 3) % 11
                unit.is_active = i % 4 != 0
            setup.absorb_battle_remains()
            rounds.append(
                {
                    'weather': battle.weather.as_report(),
                    'map': paths.asset_key(battle.map_path),
                    'radar': paths.asset_key(battle.radar_path),
                    'map_direction': battle.map_direction,
                    'field': list(battle.map_size),
                    'generated': [setup.units_to_generate_defender, setup.units_to_generate_intruder],
                    'unit_count': [len(units['Defender']), len(units['Intruder'])],
                    'totals': harness.campaign_totals(setup),
                    'should_end': setup.should_end(),
                }
            )
        out.append({'level': level, 'role': role, 'rounds': rounds})
    return out


def scenario_wars():
    """Complete wars played by the real turn logic with scripted player inputs."""
    out = []
    for level, role, deployment, skilled in itertools.product(
        ('easy', 'medium', 'hard'),
        ('Defender', 'Intruder'),
        ('inline', 'random'),
        (False, True),
    ):
        options = GameOptions(level=level, player_role=role, deployment=deployment)
        war = harness.HeadlessWar(options, game_seed=2024, aim_seed=7, skilled=skilled).run_war()
        out.append({'level': level, 'role': role, 'deployment': deployment, 'skilled': skilled, 'war': war})
    return out


def scenario_war_end_messages():
    """Final war message for every territory/damage branch."""
    out = []
    for role, territory, def_dmg, int_dmg in itertools.product(
        ('Defender', 'Intruder'),
        (-4, 0, 6, 20, 34),
        (10, 50, 400),
        (100, 150, 900),
    ):
        new_territory, message = final_war_verdict(role, 'Tester', territory, def_dmg, int_dmg)
        out.append([role, territory, def_dmg, int_dmg, new_territory, message])
    return out


SCENARIOS = {
    'shots': scenario_shots,
    'shot_scale_per_field_height': scenario_shot_scale_per_field_height,
    'damage': scenario_damage,
    'generate_units': scenario_generate_units,
    'game_setup': scenario_game_setup,
    'wars': scenario_wars,
    'war_end_messages': scenario_war_end_messages,
}


def run_scenario(name):
    result = SCENARIOS[name]()
    # Round-trip through JSON so tuples/lists compare equal to the stored file.
    return json.loads(json.dumps(result))


def golden_path(name):
    return GOLDEN_DIR / f'{name}.json'


def load_golden(name):
    return json.loads(golden_path(name).read_text(encoding='utf-8'))


def update(names):
    GOLDEN_DIR.mkdir(exist_ok=True)
    for name in names:
        data = run_scenario(name)
        with golden_path(name).open('w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
        print(f'wrote {golden_path(name)}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] != '--update':
        sys.exit(__doc__)
    update(args[1:] or list(SCENARIOS))
