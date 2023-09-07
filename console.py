import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import random
import copy
import platform
if platform.system() == "Windows":
    import ctypes
    from ctypes import windll

from settings import Settings
from units import Unit

############################################
##### Player's console (tablet) window #####
############################################

class Console:
    """A class to show commander's console and operate artillery"""

    def __init__(self, root):
        """Initialize console's attributes"""

        if platform.system() == "Windows":
            def get_scaling_factor():
                """Get scaling factor if desktop settings set to scale 125% or 150%"""
                hdc = ctypes.windll.user32.GetDC(0)
                LOGPIXELSX = 88
                actual_dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
                ctypes.windll.user32.ReleaseDC(0, hdc)
                return round(actual_dpi / 96.0, 2)

            # Mapping of screen_width to corrections based on scaling factors
            corrections = {
                2560: {
                    '125%': (23, 60),
                    '150%': (83, 120),
                    'default': (10, 5)
                },
                1920: {
                    '125%': (88, 105),
                    '150%': (190, 100),
                    'default': (8, 5)
                },
                'default': {
                    '125%': (0, 0),
                    '150%': (0, 0),
                    'default': (0, 0)
                }
            }

            scaling_factor = get_scaling_factor()

            # Determine the scaling label
            if 1.45 > scaling_factor > 1.05:
                scale_label = '125%'
            elif 2.05 > scaling_factor > 1.44:
                scale_label = '150%'
            else:
                scale_label = 'default'

            # Get the correction based on screen width and scaling label
            correction = corrections.get(Settings.screen_width, corrections['default'])[scale_label]

        else:
            scaling_factor = 1
            correction = (0, 0)

        correction_x, correction_y = correction

        # Set size of the console and place in center of the desktop
        self.screen_width = Settings.screen_width
        self.screen_height = Settings.screen_height
        self.console_width = 1200
        self.console_height = 800
        self.console_x = int((self.screen_width - self.console_width) // 2 / scaling_factor - correction_x)
        self.console_y = int((self.screen_height - self.console_height) // 2 / scaling_factor - correction_y)
        
        # Create console main window
        self.console = ctk.CTkToplevel(root, fg_color='#212121')
        self.console.geometry(f'{self.console_width}x{self.console_height}+{self.console_x}+{self.console_y}')
        self.console.minsize(self.console_width, self.console_height)
        self.console.maxsize(self.console_width, self.console_height)
        self.console.title("◗  Frontline Hardware Ltd   FIELD CONSOLE G7564")
        
        if platform.system() == "Windows":
            # Modify the window style to remove specific elements: the title bar, system menu, and resize handles.
            # Get window id
            hwnd = ctypes.windll.user32.GetParent(self.console.winfo_id())
            
            # Set the style of the window to remove the title bar
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -16) #GWL_STYLE
            style &= ~0x00080000 #WS_SYSMENU
            style &= ~0x00020000 #WS_MAXIMIZEBOX
            style &= ~0x00010000 #WS_MINIMIZEBOX
            style &= ~0x00040000 #WS_SIZEBOX

            # Apply new window style
            ctypes.windll.user32.SetWindowLongW(hwnd, -16, style)
        
        # Insert main frame for all widgets, make look like iPad
        border_frame = ctk.CTkFrame(master=self.console, fg_color="#212121", width=1200, height=825, border_width=50, border_color=("white", "#1F1F1F"))
        border_frame.place(x=0, y=-25)
        self.main_frame = ctk.CTkFrame(border_frame, width=1100, height=725, fg_color="#3D5328", border_width=0)
        self.main_frame.grid_propagate(0) # Restrict frame automatic resizing
        self.main_frame.place(x=50, y=50)
        
        # Insert navigation keys information at the bottom of main frame
        navigation_info = "'d' - for drone  'r' - for radar  'c' - for console  'w' - for withdraw  's' - for statistics"
        tk.Label(self.main_frame, text=navigation_info, bg="#3D5328", anchor="nw", bd=0, relief="solid", font=("Courier New", 14, "bold")).grid(row=3, column=0, columnspan=4, padx=10, pady=10)

class WeatherConditions(tk.LabelFrame):
    """A class to display weather conditions"""

    def __init__(self, parent, weather_conditions, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(text="Weather Conditions", bg="#3D5328", labelanchor="nw", bd=1, relief="solid", font=("TkDefaultFont", 12, "italic"))
        self.grid(row=0, column=0, padx=10, pady=10)
        for index, (label_text, value) in enumerate(weather_conditions.items()):
            label = tk.Label(self, text=label_text, bg="#3D5328", font=("Courier New", 14, "bold"))
            value_label = tk.Label(self, text=value, bg="#3D5328",  font=("Courier New", 14, "bold"))
            label.grid(row=index, column=0, sticky="w", padx=10)
            value_label.grid(row=index, sticky="e", column=1, padx=10)

class SituationReport(tk.LabelFrame):
    """A class to display situation report messages"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(text="Situation Report", bg="#3D5328", labelanchor="nw", bd=1, relief="solid", font=("TkDefaultFont", 12, "italic"))
        self.grid(row=0, column=1, columnspan=3,sticky="nsew", padx=10, pady=10)
        self.report_area = tk.Text(self, bg="#3D5328", fg="black", font=("Courier New", 14, "bold", ), cursor="double_arrow", relief="flat", height=7, width=60)
        self.report_area.configure(wrap='word') 
        self.report_area.pack()
        self.report_area.configure(state='disabled')

    def insert_message(self, report_message):
        self.report_area.configure(state='normal')
        self.report_area.insert('end', "\n" + report_message)
        self.report_area.configure(state='disabled')
        self.report_area.see('end')


class ShotParameterInput(tk.LabelFrame):
    """A class to display entry widgets for input of shot parameters"""

    def __init__(self, parent, situation_report_reference, game_loop_reference, units, **kwargs):
        super().__init__(parent,**kwargs)
        self.situation_report = situation_report_reference
        self.game_loop = game_loop_reference
        self.player_units = units[Settings.player_role]
        self.make_copy_of_units() # Create copy to be able reset to initial

        # Configure labelframe
        self.configure(text="Shot Parameter Input", bg="#3D5328", labelanchor="nw", bd=1, relief="solid", font=("TkDefaultFont", 12, "italic"))
        self.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        # Expand widgets in main frame columns 
        for column in range(1, 4):
            self.master.grid_columnconfigure(column, weight=1)
        
        # Add input fields names
        azimuth_label = tk.Label(self, text="AZIMUTH\n(0.0-±360.0)", bg="#3D5328",  font=("Courier New", 14, "bold"))
        elevation_label = tk.Label(self, text="ELEVATION\n(15.0-75.0)", bg="#3D5328", font=("Courier New", 14, "bold"))
        charge_label = tk.Label(self, text="  CHARGES\n  (1-5)", bg="#3D5328", font=("Courier New", 14, "bold"))
        azimuth_label.grid(row=1, column=0, sticky="w", padx=10)
        elevation_label.grid(row=2, sticky="w", column=0, padx=10)
        charge_label.grid(row=3, sticky="w", column=0, padx=10)
        
        # Add a list to store entry widgets
        self.entry_widgets = []

        # Add unit names and input boxes
        for unit in self.player_units:
            if unit.unit_type == "artillery":
                artillery_unit_number = f"UNIT {unit.unit_number}"
                unit_label = tk.Label(self, text=artillery_unit_number, bg="#3D5328", font=("Courier New", 14, "bold"))
                azimuth_entry = tk.Entry(self, textvariable=unit.azimuth, bg="#59782b", selectbackground="#3D5328", selectforeground="black", font=("Courier New", 14, "bold"), width=6, bd=0, justify='right', relief="solid", cursor="xterm", readonlybackground='#3D5328')
                elevation_entry = tk.Entry(self, textvariable=unit.elevation, bg="#59782b", selectbackground="#3D5328", selectforeground="black", font=("Courier New", 14, "bold"), width=6, bd=0, justify='right', relief="solid", cursor="xterm", readonlybackground='#3D5328')
                charges_entry = tk.Entry(self, textvariable=unit.charge, bg="#59782b", selectbackground="#3D5328", selectforeground="black", font=("Courier New", 14, "bold"), width=6, bd=0, justify='right', relief="solid", cursor="xterm", readonlybackground='#3D5328')
                unit_label.grid(row=0, column=unit.unit_number, sticky="ew", padx=10)
                azimuth_entry.grid(row=1, column=unit.unit_number, padx=10)
                elevation_entry.grid(row=2, column=unit.unit_number, padx=10)
                charges_entry.grid(row=3, column=unit.unit_number, padx=10)

                # Add the entries to the list along with the unit's information
                self.entry_widgets.append((azimuth_entry, unit))
                self.entry_widgets.append((elevation_entry, unit))
                self.entry_widgets.append((charges_entry, unit))

                self.grid_columnconfigure(unit.unit_number, weight=1)
            else:
                continue

        # Insert frame for the buttons
        frame_for_buttons = tk.Frame(self, bg="#3D5328")
        frame_for_buttons.grid(row=4, column=0, columnspan=int(len(self.player_units) / 2 + 1), padx=10, pady=10)

        # Add buttons to manage input and shot
        buttons = {
                "SHOW INITIAL": {   
                                    "color": "#3D5328",
                                    "state": "normal",
                                    "command": lambda: self.show_previous(self.player_units_copy),
                                    },
                "RESET": {  
                                    "color": "#3D5328",
                                    "state": "normal",
                                    "command": lambda: self.reset_to_previous(self.player_units_copy),
                                    },
                "CONFIRM": {
                                    "color": "#3D5328",
                                    "state": "normal",
                                    "command": self.confirm,
                                    },
                "FIRE": {
                                    "color": "#3D5328",
                                    "state": "disabled",
                                    "command": self.fire,
                                    },
                }
        self.buttons = {}
        for index, (text, button_configure) in enumerate(buttons.items()):
            button = tk.Button(frame_for_buttons, text=text, bg=button_configure["color"], bd=1, cursor="hand2", command=button_configure["command"], font=("Courier New", 14, "bold"), width=20, relief="flat", state=button_configure["state"], activebackground="#59782b", disabledforeground="#3D5328", overrelief="solid")
            button.grid(row=0, column=index, padx=10)
            self.buttons[text] = button

    def make_copy_of_units(self):
        self.player_units_copy = [self.copy_unit(unit) for unit in self.player_units]
        return self.player_units_copy

    def copy_unit(self, unit):
        """Function to make copy of units containing StringVar"""
        if unit.unit_type == 'artillery':
            return Unit(unit.unit_number, unit.unit_type, unit.coords, unit.image_direction, unit.player_role, unit.unit_orientation, unit.azimuth.get(), unit.elevation.get(), unit.charge.get())
        elif unit.unit_type == 'ammo':
            return Unit(unit.unit_number, unit.unit_type, unit.coords, unit.image_direction, unit.player_role, unit.unit_orientation)


    def show_previous(self, player_units_copy):
        """Shows message in status report area of previous entry values"""
        
        units_labels = ["    "]
        azimuths = []
        elevations = []
        charges = []
        
        # Prepare data
        for unit in self.player_units_copy:
            if unit.unit_type == "artillery":
                units_labels.append(f"Unt{unit.unit_number}")
                if unit.azimuth.get():
                    azimuths.append(f"{float(unit.azimuth.get())}")
                else:
                    azimuths.append('N/A')
                if unit.elevation.get():
                    elevations.append(f"{float(unit.elevation.get())}")
                else:
                    elevations.append('N/A')
                if unit.charge.get():
                    charges.append(f"{float(unit.charge.get())}")
                else:
                    charges.append('N/A')
            else:
                continue

        # Prepare the report message
        length = 27 - int(len(self.player_units_copy) * 3 / 2) # Center table
        spaces = " " * length
        report_message = "Showing initial shot parameters:\n"
        report_message += f"{spaces}" + " ".join(f"{unit_label:>5}" for unit_label in units_labels) + "\n"
        report_message += f"{spaces}" + "AZMT: " + " ".join(f"{azimuth:>5}" for azimuth in azimuths) + "\n"
        report_message += f"{spaces}" + "ELVT: " + " ".join(f"{elevation:>5}" for elevation in elevations) + "\n"
        report_message += f"{spaces}" + "CHRG: " + " ".join(f"{charge:>5}" for charge in charges) + "\n"

        self.situation_report.insert_message(report_message)

    def reset_to_previous(self, player_units_copy):
        """Resets entry widgets to previous values"""
        for entry, unit in self.entry_widgets:
            if unit.is_active: # Leave entry readonly for inactive units
                entry.config(state='normal')
        for unit, unit_copy in zip(self.player_units, self.player_units_copy):
            if unit.unit_type == 'artillery':
                if unit.is_active:
                    unit.azimuth.set(unit_copy.azimuth.get())
                    unit.elevation.set(unit_copy.elevation.get())
                    unit.charge.set(unit_copy.charge.get())
                else: # Kill unit's values if inactive
                    unit.azimuth.set("0.0")
                    unit.elevation.set("15.0")
                    unit.charge.set("1")
        self.buttons['FIRE'].config(state='disabled')
        self.buttons['CONFIRM'].config(state='normal')


    def confirm(self):
        """Checks player's input and activates 'Fire' button"""

        message = self.validate_input()
        self.situation_report.insert_message(message)
        if message == "Ready for shot":
            for entry, unit in self.entry_widgets:
                entry.config(state='readonly')
            self.buttons['FIRE'].config(state='normal')
            self.buttons['CONFIRM'].config(state='disabled')
        
    def validate_input(self):
        """Validates player input"""
        error_messages = []

        for unit in self.player_units:
            if unit.unit_type == "artillery":
                try:
                    azimuth = float(unit.azimuth.get())
                    elevation = float(unit.elevation.get())
                    charge = int(unit.charge.get())

                    if not (-360.0 <= azimuth <= 360.0):
                        error_messages.append(f"The specified azimuth of unit {unit.unit_number} is not valid.")
                    if not (15.0 <= elevation <= 75.0):
                        error_messages.append(f"The specified elevation of unit {unit.unit_number} is not valid.")
                    if not (1 <= charge <= 5):
                        error_messages.append(f"The specified charge of unit {unit.unit_number} is not valid.")

                except ValueError:
                    error_messages.append(f"The specified parameters of unit {unit.unit_number} are not valid.")

        if error_messages:
            return "\n".join(error_messages)
        else:
            return "Ready for shot"

    def fire(self):
        """Player makes shots from artillery guns and receives the same in return"""
        self.game_loop.make_turn()


class UnitStatus(tk.LabelFrame):
    """A class to display unit status"""

    def __init__(self, parent, units, **kwargs):
        super().__init__(parent, **kwargs)
        player_units = units[Settings.player_role]
        self.configure(text="Unit Status", bg="#3D5328", labelanchor="nw", bd=1, relief="solid", font=("TkDefaultFont", 12, "italic"))
        self.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        damage_label = tk.Label(self, text="DAMAGE,(%)", bg="#3D5328", font=("Courier New", 14, "bold"))
        ammo_label = tk.Label(self, text="AMMO,(pcs)", bg="#3D5328",  font=("Courier New", 14, "bold"))
        damage_label.grid(row=2, column=0, sticky="w", padx=10)
        ammo_label.grid(row=4, sticky="w", column=0, padx=10)

        for unit in player_units:
            if unit.unit_type == "artillery":
                unit_name = f"Unit {unit.unit_number}"
                unit_label = tk.Label(self, text=unit_name.upper(), bg="#3D5328", font=("Courier New", 14, "bold"))
                name_label = tk.Label(self, text=unit.name, bg="#3D5328", font=("Courier New", 14, "bold"))
                damage_label = tk.Label(self, textvariable=unit.damage, bg="#3D5328", font=("Courier New", 14, "bold"))
                unit_label.grid(row=0, column=unit.unit_number, sticky="nsew", padx=10)
                name_label.grid(row=1, column=unit.unit_number, sticky="nsew", padx=10)
                damage_label.grid(row=2, sticky="nsew", column=unit.unit_number, padx=10)
                self.grid_columnconfigure(unit.unit_number, weight=1)
            else:
                ammo_name_label = tk.Label(self, text=unit.name, bg="#3D5328", font=("Courier New", 14, "bold"))
                ammo_label = tk.Label(self, textvariable=unit.ammo, bg="#3D5328",  font=("Courier New", 14, "bold"))
                ammo_name_label.grid(row=3, column=unit.unit_number, sticky="nsew", padx=10)
                ammo_label.grid(row=4, sticky="nsew", column=unit.unit_number, padx=10)
                continue
