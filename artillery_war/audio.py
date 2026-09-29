"""Sound effects, played through pygame's mixer.

If no audio device is available (common on Linux servers, containers and some
remote sessions) the game runs silently instead of failing to start.
"""

import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame  # noqa: E402  (must follow the environment variable above)

from artillery_war import paths  # noqa: E402

SOUND_NAMES = ('blast', 'shot', 'incoming', 'destroy', 'typing')
SILENT_LENGTH = 1.0  # seconds, used for timing when sound is unavailable


class SoundManager:
    """The game's five sound effects, loaded once at start-up."""

    def __init__(self):
        self.sounds = {}
        try:
            pygame.mixer.init()
            self.sounds = {name: pygame.mixer.Sound(str(paths.SOUNDS_DIR / f'{name}.wav')) for name in SOUND_NAMES}
        except pygame.error as exc:
            print(f'Sound disabled: {exc}')

    @property
    def enabled(self):
        return bool(self.sounds)

    def length(self, name):
        """Duration of a sound in seconds, used to spread out random sound delays."""
        return self.sounds[name].get_length() if name in self.sounds else SILENT_LENGTH

    def play_sound(self, name):
        """Start playing a sound; returns immediately (timing is up to the caller)."""
        if name in self.sounds:
            self.sounds[name].play()
