"""Locations of bundled assets, independent of the current working directory."""

import sys
from pathlib import Path


def _package_dir() -> Path:
    # PyInstaller unpacks data files under sys._MEIPASS, mirroring the package layout.
    base = getattr(sys, '_MEIPASS', None)
    return Path(base) / 'artillery_war' if base else Path(__file__).resolve().parent


ASSETS_DIR = _package_dir() / 'assets'
IMAGES_DIR = ASSETS_DIR / 'images'
MAPS_DIR = IMAGES_DIR / 'maps'
UNITS_DIR = IMAGES_DIR / 'units'
SOUNDS_DIR = ASSETS_DIR / 'sounds'

ICON_ICO = IMAGES_DIR / 'icon.ico'
START_IMAGE = IMAGES_DIR / 'img_start.png'
MENU_IMAGE = IMAGES_DIR / 'img_menu.png'
BLAST_PIT_IMAGE = UNITS_DIR / 'blast_pit.png'

RULES_TEXT = ASSETS_DIR / 'rules.txt'
ABOUT_TEXT = ASSETS_DIR / 'about.txt'


def unit_image(unit_type: str, player_role: str) -> Path:
    return UNITS_DIR / f'{unit_type}_{player_role}.png'


def map_images() -> list[tuple[Path, Path]]:
    """All battlefield maps, in a stable order, each paired with its radar image."""
    maps = sorted(MAPS_DIR.glob('map*.jpg'), key=lambda p: p.name)
    return [(m, MAPS_DIR / f'radar{m.stem[3:]}.jpg') for m in maps]


def asset_key(path: str | Path) -> str:
    """Asset path relative to the assets folder, with forward slashes."""
    return Path(path).relative_to(ASSETS_DIR).as_posix()
