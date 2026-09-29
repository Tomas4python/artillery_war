"""Game balance constants and player-selectable options.

Every number in this module is part of the game balance, which was tuned by hand.
Changing any of them changes how the game plays; the golden-master tests in
``tests/`` will flag it.
"""

from dataclasses import dataclass

DEFENDER = 'Defender'
INTRUDER = 'Intruder'
ROLES = (DEFENDER, INTRUDER)

LEVELS = ('easy', 'medium', 'hard')
DEPLOYMENTS = ('inline', 'random')

DEFAULT_CALL_SIGN = 'Commander'

# Resources for the whole war, as (defender, intruder) per difficulty level.
# Damage capacity was reduced by a third in version 1.02 (from 500/1500, 1000/3000, 1500/4500).
TOTAL_AMOUNTS = {
    'easy': {'units': (10, 30), 'ammo': (100, 300), 'damage': (333, 1000)},
    'medium': {'units': (20, 60), 'ammo': (200, 600), 'damage': (667, 2000)},
    'hard': {'units': (30, 90), 'ammo': (300, 900), 'damage': (1000, 3000)},
}

# Maximum resources committed to one battle, as (defender, intruder) per difficulty level.
ROUND_AMOUNTS = {
    'easy': {'units': (1, 3), 'ammo': (10, 30), 'damage': (50, 150)},
    'medium': {'units': (2, 6), 'ammo': (20, 60), 'damage': (100, 300)},
    'hard': {'units': (3, 9), 'ammo': (30, 90), 'damage': (150, 450)},
}

# The war ends when a side drops below (units, ammo, damage). The intruder's
# thresholds are three times higher.
END_THRESHOLDS = {'easy': (1, 10, 50), 'medium': (1, 10, 50), 'hard': (1, 10, 50)}
INTRUDER_THRESHOLD_MULTIPLIER = 3

# Extra spread (pixels) of the computer's first three volleys when it plays the intruder.
FIRST_SHOTS_ACCURACY = (600, 400, 200)

# Territory, in percent, occupied by the intruder at the start of a war.
INITIAL_TERRITORY_OCCUPIED = 20
TERRITORY_PER_BATTLE = 2
TERRITORY_FRONT_BREACH = 10

# Every unit starts a battle with this much ammunition; an artillery unit is
# out of action once its damage reaches DESTROYED_DAMAGE.
UNIT_AMMO = 10
DESTROYED_DAMAGE = 50
MAX_DAMAGE = 100

# One in FAILURE_ODDS intruder guns breaks down each turn, and one in
# FAILURE_ODDS intruder shells fails to explode.
FAILURE_ODDS = 30
FAILURE_ROLL = 7

# Map pixels are converted to meters as 25 km over this image height. All maps
# are 8192 px tall, so this is the real scale of every map.
BATTLEFIELD_LENGTH_M = 25000
SCALE_REFERENCE_HEIGHT_PX = 8192

# Valid ranges for the player's firing inputs.
AZIMUTH_RANGE = (-360.0, 360.0)
ELEVATION_RANGE = (15.0, 75.0)
CHARGE_RANGE = (1, 5)


@dataclass
class GameOptions:
    """Options the player chooses in the settings menu."""

    level: str = 'easy'
    player_role: str = DEFENDER
    call_sign: str = DEFAULT_CALL_SIGN
    deployment: str = 'inline'

    @property
    def computer_role(self) -> str:
        return INTRUDER if self.player_role == DEFENDER else DEFENDER
