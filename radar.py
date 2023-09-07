import tkinter as tk
from tkinter import ttk # review
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import random

from settings import Settings
from units import Unit, generate_units

class Radar:
    """Class to create radar map view window"""

    def __init__(self, root, radar_image_path, map_direction, wind_direction, situation_report_reference):
        # Creating a new Toplevel window
        
        self.situation_report = situation_report_reference

        # Create a new Toplevel window for radar
        self.radar_window = ctk.CTkToplevel(root)
        self.radar_window.attributes('-fullscreen', True)

        # Load the radar image
        self.radar_image = Image.open(radar_image_path)

        # Re-scale image to fit screen width and set scroll region
        self.scale_factor = Settings.screen_width / self.radar_image.width
        self.radar_image = self.radar_image.resize((int(self.radar_image.width * self.scale_factor), int(self.radar_image.height * self.scale_factor)))
        self.radar_image_tk = ImageTk.PhotoImage(self.radar_image)

        # Create a frame and a canvas for the radar with associated scrollbar
        self.frame = tk.Frame(self.radar_window)
        self.frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.frame, width=Settings.screen_width, height=Settings.screen_height, bd=0, highlightthickness=0, scrollregion=(0, 0, self.radar_image.width, self.radar_image.height))        
        self.vsb = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.yview_moveto(1.0)
        
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Add mouse scroll event
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        # Add the radar image to the canvas
        self.canvas.create_image(0, 0, image=self.radar_image_tk, anchor='nw')

        # Draw grid
        km_scale_factor = self.radar_image.height / 25  # One square corresponds to 1x1 km
        step = max(int(km_scale_factor), 100)  # Ensure step is never less than 100
        correction_y = int(self.radar_image.height % step) # Start horizontal grid lines from the bottom
        correction_x = int(self.radar_image.width % step / 2) # Justify vertical grid lines
        for i in range(0 + correction_x, self.radar_image.width, step):
            self.canvas.create_line(i, 0, i, self.radar_image.height, fill="grey") # Vertical lines
        for i in range(0 + correction_y, self.radar_image.height, step):
            self.canvas.create_line(0, i, self.radar_image.width, i, fill="grey") # Horizontal lines

        # Draw scale and compass
        self.canvas.create_line(0 + 0.5 * step + correction_x, self.radar_image.height - step, 2.5 * step + correction_x, self.radar_image.height - step, fill="yellow", width=3)
        self.canvas.create_text(0 + 0.5 * step + correction_x, self.radar_image.height - step - 10, text="0", font=("Arial", 12, "bold"), fill="yellow")
        self.canvas.create_text(2.5 * step + correction_x - 2, self.radar_image.height - step - 10, text="2 km", font=("Arial", 12, "bold"), fill="yellow")
        self.canvas.create_oval(self.radar_image.width - 2.5 * step - correction_x, self.radar_image.height - 1.5 * step, self.radar_image.width - 1.5 * step - correction_x, self.radar_image.height - 0.5 * step, outline="yellow", width=2)
        # Show North direction
        map_direction_compass = 360 - map_direction + 90 # Set the compass azimuth values clockwise and 0 to the top
        wind_direction = map_direction - wind_direction
        self.canvas.create_arc(self.radar_image.width - 2.5 * step - correction_x, self.radar_image.height - 1.5 * step, self.radar_image.width - 1.5 * step - correction_x, self.radar_image.height - 0.5 * step, start=map_direction_compass, extent=1, style="pieslice", outline="yellow", width=3)        
        self.canvas.create_text(self.radar_image.width - 2 * step - correction_x, self.radar_image.height - 1 * step, text="N", font=("Arial", 30, "bold"), fill="yellow")
        # Show North in numbers and wind direction if player's role "Defender"
        if Settings.player_role == "Defender":
            self.canvas.create_oval(self.radar_image.width - 2.5 * step - correction_x - 27, self.radar_image.height - 1.5 * step - 27, self.radar_image.width - 1.5 * step - correction_x + 27, self.radar_image.height - 0.5 * step + 27, outline="yellow", width=2)
            self.canvas.create_arc(self.radar_image.width - 2.5 * step - correction_x - 20, self.radar_image.height - 1.5 * step - 20, self.radar_image.width - 1.5 * step - correction_x + 20, self.radar_image.height - 0.5 * step + 20, start=map_direction_compass, extent=1, style="pieslice", outline="yellow", width=3)        
            self.canvas.create_arc(self.radar_image.width - 2.5 * step - correction_x + 15, self.radar_image.height - 1.5 * step + 15, self.radar_image.width - 1.5 * step - correction_x - 15, self.radar_image.height - 0.5 * step - 15, start=wind_direction, extent=3, style="pieslice", outline="white", width=1, fill="white")
            self.canvas.create_text(self.radar_image.width - 2 * step - correction_x, self.radar_image.height - 0.70 * step, text=f"{map_direction}", font=("Arial", 20, "bold"), fill="yellow")
            self.canvas.create_text(self.radar_image.width - 2.5 * step - correction_x - 12, self.radar_image.height - 1 * step, text="270", fill="white", font=("Arial", 12, "bold"))
            self.canvas.create_text(self.radar_image.width - 2 * step - correction_x, self.radar_image.height - 0.5 * step + 14, text="180", fill="white", font=("Arial", 12, "bold"))
            self.canvas.create_text(self.radar_image.width - 1.5 * step - correction_x + 12, self.radar_image.height - 1  * step, text="90", fill="white", font=("Arial", 12, "bold"))
            self.canvas.create_text(self.radar_image.width - 2 * step - correction_x, self.radar_image.height - 1.5 * step - 12, text="360", fill="white", font=("Arial", 12, "bold"))
        
        # Draw arcs
        for i in range(1, int(self.radar_image.height / step + 1)):
            arc_box = (
                self.radar_image.width / 2 - i * step,
                self.radar_image.height - i * step,
                self.radar_image.width / 2 + i * step,
                self.radar_image.height
            )
            self.canvas.create_arc(arc_box, start=60, extent=60, style="arc", outline="yellow")
            self.canvas.create_text(self.radar_image.width / 2 - 2, self.radar_image.height - i * step - 8, text=str(i) + ".000", fill="yellow")

            # Blast echo count
            self.blast_echo_number_player = 0
            self.blast_echo_number_computer = 0

    def add_unit(self, unit):
        """Adds units on radar map"""

        # Scale unit coordinates
        scaled_coords = (unit.coords[0] * self.scale_factor, unit.coords[1] * self.scale_factor)
        
        # Create a circle with unit number at the scaled coordinates
        self.canvas.create_oval(scaled_coords[0] - 10, scaled_coords[1] - 10, scaled_coords[0] + 10, scaled_coords[1] + 10, outline="yellow", width=2)
        self.canvas.create_text(scaled_coords, text=str(unit.unit_number), font=("Arial", 12, "bold"), fill="yellow")

    def on_mousewheel(self, event):
        """Scrolls radar map up and down"""

        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")  # Scroll the canvas with mouse wheel

    def add_blast_echo(self, index, coords):
        """Adds blast echo arcs on radar map"""
        
        # Count blasts echoes
        blast_echo_number = self.blast_echo_number_player if index == 0 else self.blast_echo_number_computer
        blast_echo_number += 1

        # Intruders radar is not so accurate
        if Settings.player_role == "Intruder":
            less_accuracy = random.randint(-50, 50)
        else:
            less_accuracy = 0

        # Draw on radar arc of blasts echoes and add number of the blast
        x = coords[0] * self.scale_factor + less_accuracy
        y = coords[1] * self.scale_factor + less_accuracy
        arc_box = (x - 100, y - 100, x + 100, y + 100)
        self.canvas.create_arc(arc_box, start=225, extent=90, style="arc", outline="yellow", width=1)
        self.canvas.create_text(x, y + 92, text=str(blast_echo_number), fill="yellow")

        # Update the corresponding echo number
        if index == 0:
            self.blast_echo_number_player = blast_echo_number
        else:
            self.blast_echo_number_computer = blast_echo_number
        
        # Inform player about shots outside radar map borders
        if index == 0:
            out_of_range_messages = {
                "East": x < 0,
                "North": y < 0,
                "West": x > self.radar_image.width,
                "South": y > self.radar_image.height
            }
            for direction, condition in out_of_range_messages.items():
                if condition:
                    self.situation_report.insert_message(f"Shot {blast_echo_number} out of radar range {direction}")
