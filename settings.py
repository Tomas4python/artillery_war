import pygame
import os

class Settings:
    """A class to keep settings for all modules"""

    # Set initial settings (modifiable in menu)
    level = 'easy'
    player_role = 'Defender'
    call_sign = 'Commander'
    deployment = 'inline'
    # Main loop changes screen dimensions to the resolution of display (full screen)
    screen_width = 1920 
    screen_height = 1080
    # Setup module changes field dimensions to map image dimensions
    field_width = 4407
    field_height = 8192
    # Set initial game status; used for game setup and to change result windows
    game = False
    battle_results = False
    war_results = False
    end_war_results = False
    # Set initial territory occupied by intruder
    territory_occupied = 20
    # Set initial battle statistics
    battle_index = 0
    batlles_won = 0
    battles_lost = 0
    battles_tied = 0
    # Set first shots accuracy for computer if intruder
    # First three shots of intruder shall be less accurate
    first_shots_accuracy = [600, 400, 200]

    # Dict to define the total number of units, amounts of ammo and damage based on the difficulty level
    total_amounts = {   'easy': {
                                    'units': (10, 30),
                                    'ammo': (100, 300),
                                    'damage': (500, 1500)
                                },
                        'medium': {
                                    'units': (20, 60),
                                    'ammo': (200, 600),
                                    'damage': (1000, 3000)
                                },
                        'hard': {
                                    'units': (30, 90),
                                    'ammo': (300, 900),
                                    'damage': (1500, 4500)
                                },
                    }

    # Dict to define max number of units, amounts of ammo and damage based on the difficulty level for the one game round (battle)
    round_amounts = {   'easy': {
                                    'units': (1, 3),
                                    'ammo': (10, 30),
                                    'damage': (50, 150)
                                },
                        'medium': {
                                    'units': (2, 6),
                                    'ammo': (20, 60),
                                    'damage': (100, 300)
                                },
                        'hard': {
                                    'units': (3, 9),
                                    'ammo': (30, 90),
                                    'damage': (150, 450)
                                },
                    }

class SoundManager:
    """A class to manage sounds of the game"""

    def __init__(self):
        pygame.mixer.init()
        self.sounds = {}  # A dictionary to store the sounds.
        self.load_sound('blast', os.path.join('sounds', 'blast.wav'))
        self.load_sound('shot', os.path.join('sounds', 'shot.wav'))
        self.load_sound('incoming', os.path.join('sounds', 'incoming.wav'))
        self.load_sound('destroy', os.path.join('sounds', 'destroy.wav'))
        self.load_sound('typing', os.path.join('sounds', 'typing.wav'))

    def load_sound(self, name, path):
        """Load a sound from a file and store it in the dictionary."""
        sound = pygame.mixer.Sound(path)
        self.sounds[name] = sound

    def play_sound(self, name, delay=0):
        """Play a sound after an optional delay."""
        if name in self.sounds:
            pygame.time.delay(int(delay * 1000))  # delay for multiple explosions
            self.sounds[name].play()

    def stop_sound(self, name):
        """Stop a sound by its name."""
        if name in self.sounds:
            self.sounds[name].stop()