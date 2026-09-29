"""Radar view: gun positions and blast echoes on a grid scaled to the screen width."""

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

from artillery_war import platform_utils
from artillery_war.config import DEFENDER, INTRUDER
from artillery_war.core.compass import compass_point
from artillery_war.ui import theme


class RadarView:
    """Full-screen radar: map scaled to the screen width, grid, range arcs, compass."""

    def __init__(
        self, root, radar_image_path, map_direction, wind_direction, situation_report, player_role, screen, rng
    ):
        """``screen`` is (width, height); ``rng`` only jitters the intruder's radar echoes (cosmetic)."""
        self.situation_report = situation_report
        self.player_role = player_role
        self.map_direction = map_direction
        self.rng = rng
        screen_width, screen_height = screen

        self.radar_window = ctk.CTkToplevel(root)
        self.radar_window.attributes('-fullscreen', True)

        # Scale the radar image to the screen width.
        image = Image.open(radar_image_path)
        self.scale_factor = screen_width / image.width
        size = (int(image.width * self.scale_factor), int(image.height * self.scale_factor))
        image.draft('RGB', size)  # JPEG: decode at a reduced scale when that is still at least `size`
        self.radar_image_tk = ImageTk.PhotoImage(image.resize(size, reducing_gap=3.0))
        self.width, self.height = width, height = size

        self.frame = tk.Frame(self.radar_window)
        self.frame.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(
            self.frame,
            width=screen_width,
            height=screen_height,
            bd=0,
            highlightthickness=0,
            scrollregion=(0, 0, width, height),
        )
        self.vsb = tk.Scrollbar(self.frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.yview_moveto(1.0)
        self.vsb.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        platform_utils.bind_mousewheel(self.canvas, lambda steps: self.canvas.yview_scroll(steps, 'units'))

        self.canvas.create_image(0, 0, image=self.radar_image_tk, anchor='nw')

        # 1 km grid (at least 100 px), aligned to the bottom edge and centered horizontally.
        step = max(int(height / 25), 100)
        correction_y = int(height % step)
        correction_x = int(width % step / 2)
        for i in range(correction_x, width, step):
            self.canvas.create_line(i, 0, i, height, fill='grey')
        for i in range(correction_y, height, step):
            self.canvas.create_line(0, i, width, i, fill='grey')

        # Scale bar.
        bar_y = height - step
        self.canvas.create_line(
            0.5 * step + correction_x, bar_y, 2.5 * step + correction_x, bar_y, fill=theme.RADAR, width=3
        )
        self.canvas.create_text(
            0.5 * step + correction_x, bar_y - 10, text='0', font=theme.RADAR_FONT, fill=theme.RADAR
        )
        self.canvas.create_text(
            2.5 * step + correction_x - 2, bar_y - 10, text='2 km', font=theme.RADAR_FONT, fill=theme.RADAR
        )

        # Compass, bottom right. Canvas arcs start at 3 o'clock and run anticlockwise.
        left = width - 2.5 * step - correction_x
        right = width - 1.5 * step - correction_x
        top = height - 1.5 * step
        bottom = height - 0.5 * step
        center_x = width - 2 * step - correction_x
        self.canvas.create_oval(left, top, right, bottom, outline=theme.RADAR, width=2)
        north = 360 - map_direction + 90
        wind = map_direction - wind_direction
        self.canvas.create_arc(
            left, top, right, bottom, start=north, extent=1, style='pieslice', outline=theme.RADAR, width=3
        )
        self.canvas.create_text(center_x, height - step, text='N', font=(theme.SANS, 30, 'bold'), fill=theme.RADAR)

        if player_role == DEFENDER:
            # The defender also gets the bearing of north in numbers and the wind direction.
            self.canvas.create_oval(left - 27, top - 27, right + 27, bottom + 27, outline=theme.RADAR, width=2)
            self.canvas.create_arc(
                left - 20,
                top - 20,
                right + 20,
                bottom + 20,
                start=north,
                extent=1,
                style='pieslice',
                outline=theme.RADAR,
                width=3,
            )
            self.canvas.create_arc(
                left + 15,
                top + 15,
                right - 15,
                bottom - 15,
                start=wind,
                extent=3,
                style='pieslice',
                outline='white',
                width=1,
                fill='white',
            )
            self.canvas.create_text(
                center_x, height - 0.70 * step, text=f'{map_direction}', font=(theme.SANS, 20, 'bold'), fill=theme.RADAR
            )
            for x, y, text in (
                (left - 12, height - step, '270'),
                (center_x, bottom + 14, '180'),
                (right + 12, height - step, '90'),
                (center_x, top - 12, '360'),
            ):
                self.canvas.create_text(x, y, text=text, fill='white', font=theme.RADAR_FONT)

        # Range arcs from the bottom center, one per grid step.
        for i in range(1, int(height / step + 1)):
            arc_box = (width / 2 - i * step, height - i * step, width / 2 + i * step, height)
            self.canvas.create_arc(arc_box, start=60, extent=60, style='arc', outline=theme.RADAR)
            self.canvas.create_text(width / 2 - 2, height - i * step - 8, text=str(i) + '.000', fill=theme.RADAR)

        self.blast_echo_number_player = 0
        self.blast_echo_number_computer = 0

    def add_unit(self, unit):
        """Mark a gun as a numbered circle."""
        x, y = unit.coords[0] * self.scale_factor, unit.coords[1] * self.scale_factor
        self.canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline=theme.RADAR, width=2)
        self.canvas.create_text((x, y), text=str(unit.unit_number), font=theme.RADAR_FONT, fill=theme.RADAR)

    def add_blast_echo(self, index, coords):
        """Draw a numbered echo arc; ``index`` 0 is the player's shell, 1 the computer's."""
        if index == 0:
            self.blast_echo_number_player += 1
            number = self.blast_echo_number_player
        else:
            self.blast_echo_number_computer += 1
            number = self.blast_echo_number_computer

        # The intruder's radar is less accurate.
        jitter = self.rng.randint(-50, 50) if self.player_role == INTRUDER else 0
        x = coords[0] * self.scale_factor + jitter
        y = coords[1] * self.scale_factor + jitter
        self.canvas.create_arc(
            (x - 100, y - 100, x + 100, y + 100), start=225, extent=90, style='arc', outline=theme.RADAR, width=1
        )
        self.canvas.create_text(x, y + 92, text=str(number), fill=theme.RADAR)

        if index == 0 and not (0 <= x <= self.width and 0 <= y <= self.height):
            # Name the true compass direction of the landing point, seen from the player's position
            # (bottom center, where the radar's range arcs start), not the screen edge it crossed:
            # the map is rotated by map_direction (see core/compass.py).
            direction = compass_point(x - self.width / 2, y - self.height, self.map_direction)
            self.situation_report.insert_message(f'Shot {number} out of radar range {direction}')
