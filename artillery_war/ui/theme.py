"""Colors and fonts shared by all windows.

Font families are resolved at start-up (``configure_fonts``) because the
Windows fonts the game was designed with are usually missing on Linux. The
reports are laid out in columns, so the monospaced fallback matters.
"""

import tkinter.font as tkfont

KHAKI = '#3D5328'  # panel background
KHAKI_LIGHT = '#59782b'  # entries, hover
BEZEL = '#2E3522'  # tablet frame, dark olive 'special edition'
BEZEL_RIM = '#56603F'  # thin lighter edge around the bezel
CAMERA = '#141711'
BRAND_TEXT = '#A3AE82'
BACKDROP = '#212121'  # window background behind the tablet
TEXT = 'black'
MUTED = '#818589'
RADAR = 'yellow'

MONO_CANDIDATES = ('Courier New', 'Liberation Mono', 'DejaVu Sans Mono', 'Nimbus Mono PS', 'Courier')
SANS_CANDIDATES = ('Arial', 'Liberation Sans', 'DejaVu Sans', 'Nimbus Sans', 'Helvetica')

MONO = MONO_CANDIDATES[0]
SANS = SANS_CANDIDATES[0]


# Fonts are (family, size, style) tuples; _derive_fonts rebuilds them after configure_fonts.
CONSOLE_FONT = REPORT_FONT = MENU_FONT = BATTLE_LABEL_FONT = RADAR_FONT = (MONO, 12, 'bold')


def _derive_fonts():
    global CONSOLE_FONT, REPORT_FONT, MENU_FONT, BATTLE_LABEL_FONT, RADAR_FONT
    CONSOLE_FONT = (MONO, 14, 'bold')
    REPORT_FONT = (MONO, 20, 'bold')
    MENU_FONT = (SANS, 40, 'bold')
    BATTLE_LABEL_FONT = (MONO, 70, 'bold')
    RADAR_FONT = (SANS, 12, 'bold')


FRAME_TITLE_FONT = ('TkDefaultFont', 12, 'italic')
_derive_fonts()


def _first_available(candidates, available, fallback):
    for family in candidates:
        if family.lower() in available:
            return family
    return fallback


def configure_fonts(root):
    """Pick the first installed family of each kind; call once the Tk root exists."""
    global MONO, SANS
    available = {family.lower() for family in tkfont.families(root)}
    MONO = _first_available(MONO_CANDIDATES, available, tkfont.nametofont('TkFixedFont', root).actual('family'))
    SANS = _first_available(SANS_CANDIDATES, available, tkfont.nametofont('TkDefaultFont', root).actual('family'))
    _derive_fonts()
