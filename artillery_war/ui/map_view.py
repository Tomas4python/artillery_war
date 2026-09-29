"""Drone view: the full-resolution battlefield map with units and blast pits (defender only).

The map image is 4407 x 8192 px. Turning it into one Tk image costs ~150 MB and a
second of start-up, so it is drawn as tiles, created only for the part in view.
"""

import functools
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

from artillery_war import paths, platform_utils

TILE = 512  # px
GLIDE_STEPS = 5  # arrow keys scroll in 5 small steps...
GLIDE_INTERVAL_MS = 100  # ...100 ms apart


@functools.cache
def _sprite(unit_type, player_role):
    """Unit sprite at half size (the PNGs are 100 x 100)."""
    image = Image.open(paths.unit_image(unit_type, player_role))
    return image.resize((image.width // 2, image.height // 2), Image.LANCZOS)


class MapView:
    """Full-screen drone window showing the real map, units and blast pits."""

    def __init__(self, root, map_image_path, screen, map_size):
        screen_width, screen_height = screen
        self.map_window = ctk.CTkToplevel(root)
        self.map_window.attributes('-fullscreen', True)

        self.map_image = Image.open(map_image_path)
        self.map_image.load()
        self.tiles = {}  # (column, row) -> PhotoImage
        self._tiles_pending = False

        self.canvas = tk.Canvas(
            self.map_window,
            width=screen_width,
            height=screen_height,
            bd=0,
            highlightthickness=0,
            scrollregion=(0, 0, self.map_image.width, self.map_image.height),
            xscrollcommand=self._view_changed,
            yscrollcommand=self._view_changed,
        )
        self.canvas.pack()

        # Drag the map with the left mouse button, or scroll it with the wheel.
        self.canvas.bind('<ButtonPress-1>', self.start_move)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<Configure>', self._view_changed)
        platform_utils.bind_mousewheel(self.canvas, lambda steps: self.canvas.yview_scroll(steps, 'units'))

        # Keep references to PhotoImages, or tkinter garbage-collects them.
        self.unit_images = {}
        self.blast_image = ImageTk.PhotoImage(Image.open(paths.BLAST_PIT_IMAGE))

        # Start at the bottom of the map, where the player's units are.
        self.canvas.xview_moveto(screen_width / map_size[0] / 2)
        self.canvas.yview_moveto(1)

        self.map_window.bind('<Left>', lambda event: self._glide(self.canvas.xview_scroll, -1))
        self.map_window.bind('<Right>', lambda event: self._glide(self.canvas.xview_scroll, 1))
        self.map_window.bind('<Up>', lambda event: self._glide(self.canvas.yview_scroll, -1))
        self.map_window.bind('<Down>', lambda event: self._glide(self.canvas.yview_scroll, 1))
        self.canvas.focus_set()

    # ------------------------------------------------------------ tiles

    def _view_changed(self, *_args):
        """Called by every scroll/resize; draws missing tiles once the view settles."""
        if not self._tiles_pending:
            self._tiles_pending = True
            # PyCharm misreads the *args type of after_idle:
            # noinspection PyTypeChecker
            self.canvas.after_idle(self._draw_visible_tiles)

    def _draw_visible_tiles(self):
        self._tiles_pending = False
        if not self.canvas.winfo_exists():
            return
        left = self.canvas.canvasx(0)
        top = self.canvas.canvasy(0)
        right = left + self.canvas.winfo_width()
        bottom = top + self.canvas.winfo_height()
        columns = range(max(int(left) // TILE, 0), min(int(right) // TILE, (self.map_image.width - 1) // TILE) + 1)
        rows = range(max(int(top) // TILE, 0), min(int(bottom) // TILE, (self.map_image.height - 1) // TILE) + 1)
        for column in columns:
            for row in rows:
                if (column, row) not in self.tiles:
                    x, y = column * TILE, row * TILE
                    box = (x, y, min(x + TILE, self.map_image.width), min(y + TILE, self.map_image.height))
                    self.tiles[column, row] = tile = ImageTk.PhotoImage(self.map_image.crop(box))
                    self.canvas.create_image(x, y, image=tile, anchor='nw', tags='tile')
        self.canvas.tag_lower('tile')  # units and blast pits stay on top

    # --------------------------------------------------------- scrolling

    def start_move(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=2)

    def _glide(self, view_scroll, direction, steps_left=GLIDE_STEPS):
        """Scroll one unit now and the rest later, without blocking the event loop."""
        if steps_left and self.canvas.winfo_exists():
            view_scroll(direction, 'units')
            self.canvas.after(GLIDE_INTERVAL_MS, self._glide, view_scroll, direction, steps_left - 1)

    # ------------------------------------------------------------ units

    def add_unit(self, unit):
        """Draw a unit's sprite, rotated to face its direction (trucks towards their gun)."""
        unit_image = _sprite(unit.unit_type, unit.player_role)
        # Sprites face north; southern-facing units are turned round first.
        if unit.image_direction == 'south':
            unit_image = unit_image.rotate(180)
        unit_image = unit_image.rotate(unit.unit_orientation)

        unit_image_tk = ImageTk.PhotoImage(unit_image)
        x, y = unit.coords
        self.canvas.create_image(x, y, image=unit_image_tk, anchor='center', tags='unit')
        self.unit_images[unit] = unit_image_tk

    def add_blast_pit(self, coords):
        x, y = coords
        self.canvas.create_image(x, y, image=self.blast_image, anchor='center', tags='blast')
