"""Events a battle turn produces, replayed in order by the user interface."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Message:
    """A line for the console's situation report."""

    text: str


@dataclass(frozen=True)
class Sound:
    """A sound to play, after either a fixed ``delay`` (seconds) or a random ``spread``.

    ``spread`` is a number in [0, 1) that the interface maps onto the sound's own
    length, so the core does not need to know how long each sound file is.
    """

    name: str
    delay: float | None = None
    spread: float | None = None

    def delay_for(self, sound_length: float, minimum: float = 0.3) -> float:
        if self.delay is not None:
            return self.delay
        assert self.spread is not None, 'a sound needs a delay or a spread'
        return minimum + (sound_length - minimum) * self.spread


@dataclass(frozen=True)
class Blasts:
    """Where this turn's shells exploded, for the drone map and radar."""

    player: list[tuple[int, int]] = field(default_factory=list)
    computer: list[tuple[int, int]] = field(default_factory=list)


@dataclass(frozen=True)
class BattleOver:
    """The battle has ended; the outcome is in ``Battle.outcome``."""


Event = Message | Sound | Blasts | BattleOver
