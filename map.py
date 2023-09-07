import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import time

from settings import Settings
from units import Unit, generate_units

class Map:
    """Class to create drone map view window"""

    def __init__(self, root, map_image_path):

        # Create a new Toplevel window for drone view
        self.map_window = ctk.CTkToplevel(root)
        self.map_window.attributes('-fullscreen', True)

        # Load the map image
        self.map_image = Image.open(map_image_path)
        self.map_image_tk = ImageTk.PhotoImage(self.map_image)

        # Create a canvas for the map
        self.canvas = tk.Canvas(self.map_window, width=self.map_window.winfo_screenwidth(), height=self.map_window.winfo_screenheight(), bd=0, highlightthickness=0, scrollregion=(0, 0, self.map_image.width, self.map_image.height))
        self.canvas.pack()

        # Add the map image to the canvas
        self.canvas.create_image(0, 0, image=self.map_image_tk, anchor='nw')

        # Variables for scrolling functionality
        self.last_x = 0
        self.last_y = 0

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_move)

        # Dictionary to hold unit and blast images
        self.unit_images = {}
        self.blast_images = {}

        # Move view to the bottom of the map
        self.canvas.xview_moveto(Settings.screen_width / Settings.field_width / 2)
        self.canvas.yview_moveto(1)

        # Bind the keyboard arrow keys to the scrolling functions
        self.map_window.bind("<Left>", self.scroll_left)
        self.map_window.bind("<Right>", self.scroll_right)
        self.map_window.bind("<Up>", self.scroll_up)
        self.map_window.bind("<Down>", self.scroll_down)
        self.canvas.focus_set()

    # Functions to operate map image movements in map window
    def start_move(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=2)

    def stop_move(self, event):
        pass

    def scroll_left(self, event):
        for _ in range(5):
            self.canvas.xview_scroll(-1, 'units')
            self.map_window.update_idletasks()
            time.sleep(0.1)

    def scroll_right(self, event):
        for _ in range(5):
            self.canvas.xview_scroll(1, 'units')
            self.map_window.update_idletasks()
            time.sleep(0.1)

    def scroll_up(self, event):
        for _ in range(5):
            self.canvas.yview_scroll(-1, 'units')
            self.map_window.update_idletasks()
            time.sleep(0.1)

    def scroll_down(self, event):
        for _ in range(5):
            self.canvas.yview_scroll(1, 'units')
            self.map_window.update_idletasks()
            time.sleep(0.1)

    def add_unit(self, unit):
        # Define the image name based on the unit type and player
        image_name = f"{unit.unit_type}_{unit.player_role}.png"

        # Load the unit image
        image_path = os.path.join(r'images', 'units', image_name)
        unit_image = Image.open(image_path)
        
        # Get the current image size
        width, height = unit_image.size

        # Calculate the new size
        new_size = (width//2, height//2)

        # Resize the image
        unit_image = unit_image.resize(new_size, Image.ANTIALIAS)

        # Rotate the image based on the direction and artillery position
        if unit.image_direction == 'south':
            unit_image = unit_image.rotate(180)
            unit_image = unit_image.rotate(unit.unit_orientation)
        else:
            unit_image = unit_image.rotate(unit.unit_orientation)

        unit_image_tk = ImageTk.PhotoImage(unit_image)

        # Add the unit image to the canvas
        x, y = unit.coords
        self.canvas.create_image(x, y, image=unit_image_tk, anchor='center', tags='unit')

        # Store the unit image to prevent garbage collection
        self.unit_images[unit] = unit_image_tk

    def add_blast_pit(self, coords):
        """Adds blast pit image to the map"""

        # Load the blast pit image
        image_path = os.path.join(r'images' ,'units', 'blast_pit.png')
        blast_image = Image.open(image_path)
        blast_image_tk = ImageTk.PhotoImage(blast_image)

        # Add the blast pit image to the canvas at the given coordinates
        x, y = coords
        self.canvas.create_image(x, y, image=blast_image_tk, anchor='center', tags='blast')

        # Store the blast pit image to prevent garbage collection
        self.blast_images[coords] = blast_image_tk

