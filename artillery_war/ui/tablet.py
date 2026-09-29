"""The rugged 'tablet' look shared by the field console and the report screen.

The bezel is rendered with Pillow (rounded corners, rim, camera) and shown as
the background image of a label; the screen content is placed on top of it.
``TabletWindow`` is the borderless, draggable window version used during a battle.
"""

import functools
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from artillery_war import platform_utils
from artillery_war.ui import theme

BRAND = '◗  Frontline Hardware Ltd   FIELD CONSOLE G7564'
# One size for every tablet (field console and reports), so they line up exactly.
TABLET_WIDTH = 1200
TABLET_HEIGHT = 825
BEZEL_WIDTH = 50  # around a 1100 x 725 screen
CORNER_RADIUS = 36
SCREEN_RADIUS = 6
SUPERSAMPLE = 4

# Color made transparent by the window manager around the console's rounded corners (Windows only).
TRANSPARENT_KEY = '#ff00fe'
CAN_CUT_CORNERS = platform_utils.IS_WINDOWS


def _rgb(color):
    color = color.lstrip('#')
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


@functools.cache
def render_tablet(width: int, height: int, corner_radius: int = CORNER_RADIUS) -> Image.Image:
    """RGBA image of the tablet: bezel with rim and camera, and the (empty) screen area."""
    s = SUPERSAMPLE
    image = Image.new('RGBA', (width * s, height * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outer = (0, 0, width * s - 1, height * s - 1)
    draw.rounded_rectangle(outer, radius=corner_radius * s, fill=_rgb(theme.BEZEL_RIM))
    rim = 2 * s
    draw.rounded_rectangle(
        (rim, rim, width * s - 1 - rim, height * s - 1 - rim),
        radius=max(corner_radius - 2, 0) * s,
        fill=_rgb(theme.BEZEL),
    )
    b = BEZEL_WIDTH * s
    draw.rounded_rectangle(
        (b, b, width * s - 1 - b, height * s - 1 - b), radius=SCREEN_RADIUS * s, fill=_rgb(theme.KHAKI)
    )
    # Front camera, centered on the top edge.
    cx, cy, r = width * s // 2, b // 2, 4 * s
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_rgb(theme.CAMERA))
    return image.reduce(s)  # average each s x s block: smooth, anti-aliased edges


def on_background(tablet: Image.Image, background: Image.Image) -> Image.Image:
    """Composite the tablet over the background it will be shown on (smooth corners)."""
    result = background.convert('RGB').copy()
    result.paste(tablet, (0, 0), tablet)
    return result


def on_key_color(tablet: Image.Image, key: str) -> Image.Image:
    """Flatten the tablet for a window whose ``key`` color is transparent (hard-edged corners)."""
    solid = Image.new('RGB', tablet.size, _rgb(theme.BEZEL_RIM))
    solid.paste(tablet, (0, 0), tablet)
    mask = tablet.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    result = Image.new('RGB', tablet.size, _rgb(key))
    result.paste(solid, (0, 0), mask)
    return result


class Tablet(tk.Label):
    """A label showing the tablet image, with the brand printed on the bezel.

    Place content inside it at (BEZEL_WIDTH, BEZEL_WIDTH); the screen is
    ``width - 2 * BEZEL_WIDTH`` by ``height - 2 * BEZEL_WIDTH`` pixels.
    """

    def __init__(self, master, width, height, background: Image.Image | None = None, key: str = TRANSPARENT_KEY):
        # A window can only have rounded corners where the platform can make its corners transparent.
        rounded = background is not None or CAN_CUT_CORNERS
        tablet = render_tablet(width, height, CORNER_RADIUS if rounded else 0)
        image = on_background(tablet, background) if background is not None else on_key_color(tablet, key)
        self.photo = ImageTk.PhotoImage(image)
        super().__init__(master, image=self.photo, bd=0, highlightthickness=0, bg=theme.KHAKI)
        self.brand = tk.Label(
            self, text=BRAND, bg=theme.BEZEL, fg=theme.BRAND_TEXT, font=(theme.SANS, 10), bd=0, padx=0, pady=0
        )
        self.brand.place(x=CORNER_RADIUS, y=BEZEL_WIDTH // 2, anchor='w')

    @property
    def screen_size(self):
        return self.photo.width() - 2 * BEZEL_WIDTH, self.photo.height() - 2 * BEZEL_WIDTH


# Hand-tuned position corrections per screen width and Windows scaling (125% / 150%).
# At 100% the tablet is frameless and centered exactly.
_SCALED_CORRECTIONS = {
    2560: {'125%': (23, 60), '150%': (83, 120), 'default': (0, 0)},
    1920: {'125%': (88, 105), '150%': (190, 100), 'default': (0, 0)},
    'default': {'125%': (0, 0), '150%': (0, 0), 'default': (0, 0)},
}
KEEP_VISIBLE = 150  # px of the tablet that must stay on screen when it is dragged


def default_tablet_position(screen_width, screen_height):
    """Top-left corner that centers a tablet window on the screen."""
    scaling_factor = platform_utils.desktop_scaling()
    if 1.45 > scaling_factor > 1.05:
        scale_label = '125%'
    elif 2.05 > scaling_factor > 1.44:
        scale_label = '150%'
    else:
        scale_label = 'default'
    correction_x, correction_y = _SCALED_CORRECTIONS.get(screen_width, _SCALED_CORRECTIONS['default'])[scale_label]
    x = int((screen_width - TABLET_WIDTH) // 2 / scaling_factor - correction_x)
    y = int((screen_height - TABLET_HEIGHT) // 2 / scaling_factor - correction_y)
    return x, y


class TabletWindow:
    """A borderless window that is just the tablet; drag it by its bezel to move it.

    ``main_frame`` is the screen to put content on. ``on_drag(x, y)`` is called on
    every movement while dragging, ``on_moved(x, y)`` when the player lets go.
    """

    def __init__(self, root, position, on_moved=None, title='Field console'):
        self.on_moved = on_moved
        self.on_drag = None
        self._position = tuple(position)
        backdrop = TRANSPARENT_KEY if CAN_CUT_CORNERS else theme.BACKDROP
        self.window = ctk.CTkToplevel(root, fg_color=backdrop)
        self.window.geometry(f'{TABLET_WIDTH}x{TABLET_HEIGHT}+{position[0]}+{position[1]}')
        self.window.minsize(TABLET_WIDTH, TABLET_HEIGHT)
        self.window.maxsize(TABLET_WIDTH, TABLET_HEIGHT)
        self.window.title(title)

        # No title bar or window frame: the window is just the tablet, with its corners cut away.
        self.window.overrideredirect(True)
        if CAN_CUT_CORNERS:
            self.window.attributes('-transparentcolor', TRANSPARENT_KEY)

        self.tablet = Tablet(self.window, TABLET_WIDTH, TABLET_HEIGHT, key=backdrop)
        self.tablet.place(x=0, y=0)
        screen_width, screen_height = self.tablet.screen_size
        self.main_frame = tk.Frame(self.tablet, width=screen_width, height=screen_height, bg=theme.KHAKI)
        self.main_frame.grid_propagate(False)
        self.main_frame.place(x=BEZEL_WIDTH, y=BEZEL_WIDTH)

        # The screen covers the middle, so only the bezel (and the brand on it) starts a drag.
        self._grab = None
        for handle in (self.tablet, self.tablet.brand):
            handle.configure(cursor='fleur')
            handle.bind('<ButtonPress-1>', self._start_drag)
            handle.bind('<B1-Motion>', self._drag)
            handle.bind('<ButtonRelease-1>', self._end_drag)

    @property
    def position(self):
        return self._position

    def move_to(self, x, y):
        self._position = (x, y)
        self.window.geometry(f'+{x}+{y}')

    def _start_drag(self, event):
        x, y = self.position
        self._grab = (event.x_root - x, event.y_root - y)

    def _drag(self, event):
        if self._grab is None:
            return
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = event.x_root - self._grab[0]
        y = event.y_root - self._grab[1]
        # Keep part of the tablet, and its top bezel, on screen so it can always be grabbed again.
        x = min(max(x, KEEP_VISIBLE - TABLET_WIDTH), screen_width - KEEP_VISIBLE)
        y = min(max(y, 0), screen_height - KEEP_VISIBLE)
        self.move_to(x, y)
        if self.on_drag is not None:
            self.on_drag(x, y)

    def _end_drag(self, event):
        if self._grab is None:
            return
        self._drag(event)  # the last movement can arrive together with the release
        self._grab = None
        if self.on_moved is not None:
            self.on_moved(*self.position)
