import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import platform
if platform.system() == "Windows":
    from ctypes import windll

# Import application modules
from settings import Settings
from game_loop import Play


################################
##### Main loop of the app #####
################################

class Game:
    """Class to run the app, main tkinter loop, root window, manage welcome screen and menu screen"""

    def __init__(self):
        
        if platform.system() == "Windows":
            # Set DPI Awareness
            windll.shcore.SetProcessDpiAwareness(2)
        
        # Set dark mode
        ctk.set_appearance_mode("dark")  # Available modes: system (default), light, dark

        # Create main window for app, start screen and menu
        self.root = ctk.CTk()
        self.root.attributes('-fullscreen',True)
        icon_path = os.path.join(os.getcwd(), 'images', 'icon.ico')
        self.root.iconbitmap(icon_path)
        self.root.update()
        
        # Set screen dimensions for all modules
        self.root.update_idletasks()
        Settings.screen_width = self.root.winfo_screenwidth()
        Settings.screen_height = self.root.winfo_screenheight()
        
        # Open images for welcome and menu screens
        start_image_path = os.path.join(os.getcwd(), 'images', 'img_start.png')
        menu_image_path = os.path.join(os.getcwd(), 'images', 'img_menu.png')
        self.start_image = ctk.CTkImage(light_image=Image.open(start_image_path), dark_image=Image.open(start_image_path), size=(1152, 720))
        self.menu_image = ctk.CTkImage(light_image=Image.open(menu_image_path), dark_image=Image.open(menu_image_path), size=(Settings.screen_width, Settings.screen_height))
        
        # Initiate game loop class Play
        self.play = Play(self)

        # Set variable for the player name (call-sign)
        self.callsign = tk.StringVar()

        # Open start screen
        self.create_image_label()
        self.create_instruction_label()
        
        # Open menu
        self.create_menu_buttons()

        # Bind keyboard keys for navigation
        self.root.bind_all('q', self.ask_quit)        
        self.root.bind('<space>', lambda event: self.show_menu('main'))

    def create_image_label(self):
        self.image_label = ctk.CTkLabel(master=self.root, image=self.start_image, text="")
        self.image_label.place(x=0, y=0, relwidth=1, relheight=1)

    def create_instruction_label(self):
        self.instruction_label = ctk.CTkLabel(master=self.root, text="Press 'Space' to continue", font=('Courier New', 24), text_color="#818589")
        self.instruction_label.place(relx=0.5, rely=0.97, anchor='center')


#####################################
##### Menu buttons and commands #####
#####################################

    def create_menu_buttons(self):
        
        menus = {
            'main': {
                    'buttons': [
                            'Play the game',
                            'Settings',
                            'Rules',
                            'About',
                            '[Q]uit',
                            ],
                    'commands': [
                            self.play.play_the_game,
                            self.show_different_menu('settings'),
                            self.display_rules,
                            self.display_about,
                            self.ask_quit,
                        ]
            },
            'settings': {
                    'buttons': [
                            'Callsign',
                            'Choose player',
                            'Difficulty',
                            'Deployment',
                            'Back to main',
                            ],
                    'commands': [
                            self.get_callsign,
                            self.show_different_menu('player'),
                            self.show_different_menu('difficulty'),
                            self.show_different_menu('deployment'),
                            self.show_different_menu('main'),
                        ]
            },
            'player': {
                    'buttons': [
                            'Defender',
                            'Invader',
                            ],
                    'commands': [
                            self.choose_defender,
                            self.choose_intruder,
                        ],
            },
            'difficulty': {
                    'buttons': [
                            'Easy',
                            'Medium',
                            'Hard',
                            ],
                    'commands': [
                            self.choose_easy,
                            self.choose_medium,
                            self.choose_hard,
                        ],
            },
            'deployment': {
                    'buttons': [
                            'Inline',
                            'Random',
                            ],
                    'commands': [
                            self.choose_inline,
                            self.choose_random,
                        ]
            },
        }

        self.buttons = {} # Store all buttons
        self.button_frame = ctk.CTkFrame(master=self.root, fg_color="#59782b") # Create frame for the buttons
        self.button_frame.place(relx=0.5, rely=0.5, anchor='center')
        self.button_frame.lower()# Hide frame initially under other widgets

        for menu_name, menu_info in menus.items():
            self.buttons[menu_name] = [] # Create dictionary of button lists for different menu layers
            for text, command in zip(menu_info['buttons'], menu_info['commands']):
                button = ctk.CTkButton(master=self.button_frame, text=text, command=command, corner_radius=10, border_width=5, border_spacing=5, fg_color="#3D5328", hover_color="#59782b" ,border_color="black", text_color="black",  font=('Arial', 40, "bold"))
                self.buttons[menu_name].append(button)

    def show_menu(self, menu_name):
        
        self.root.unbind('<space>')
        self.image_label.configure(image=self.menu_image)
        self.instruction_label.place_forget()
        self.button_frame.lift()
        
        self.hide_all_buttons()

        for self.button in self.buttons[menu_name]:
            self.button.pack(padx= 0, pady=0, fill='x')

    def show_different_menu(self, menu_name):
        return lambda: self.show_menu(menu_name)

    def hide_all_buttons(self):
        for button_list in self.buttons.values():
            for button in button_list:
                button.pack_forget()      

    def get_callsign(self):
        self.hide_all_buttons()
        self.callsign_label = ctk.CTkLabel(master=self.button_frame, text=" At least 2 characters: ", corner_radius = 0, fg_color="#3D5328", text_color="black",  font=("Arial", 40, "bold"))
        self.callsign.set(Settings.call_sign)
        self.callsign_entry = ctk.CTkEntry(master=self.button_frame, textvariable=self.callsign, justify="center", corner_radius = 0, fg_color="#59782b", text_color="black", placeholder_text="", font=("Courier New", 40, "bold"))
        self.callsign_entry.focus()
        self.callsign_button = ctk.CTkButton(master=self.button_frame, text=" Set your callsign ", command=self.set_callsign, corner_radius=10, border_width=5, border_spacing=5, fg_color="#3D5328", hover_color="#59782b" ,border_color="black", text_color="black", font=('Arial', 40, "bold"))
        self.callsign_label.pack(padx= 0, pady=0, fill='x')
        self.callsign_entry.pack(padx= 0, pady=0, fill='x')
        self.callsign_button.pack(padx= 0, pady=0, fill='x')

    def set_callsign(self):
        callsign = self.callsign.get()
        Settings.call_sign =  callsign if len(callsign) > 1 else "Commander"
        self.callsign_label.pack_forget()
        self.callsign_entry.pack_forget()
        self.callsign_button.pack_forget()
        self.show_menu('settings')

    def choose_defender(self):
        Settings.player_role = 'Defender'
        self.hide_all_buttons()
        self.show_menu('settings')

    def choose_intruder(self):
        Settings.player_role = 'Intruder'
        self.hide_all_buttons()
        self.show_menu('settings')

    def choose_easy(self):
        Settings.level = 'easy'
        self.hide_all_buttons()
        selfBshow_menu('settings')

    def choose_medium(self):
        Settings.level = 'medium'
        self.hide_all_buttons()
        self.show_menu('settings')

    def choose_hard(self):
        Settings.level = 'hard'
        self.hide_all_buttons()
        self.show_menu('settings')
    
    def choose_inline(self):
        Settings.deployment = 'inline'
        self.hide_all_buttons()
        self.show_menu('settings')
    
    def choose_random(self):
        Settings.deployment = 'random'
        self.hide_all_buttons()
        self.show_menu('settings')

    def display_txt_file(self, filename):

        self.hide_all_buttons()
    
        # Add frames for textbox widget and button with tablet look
        self.border_frame = ctk.CTkFrame(master=self.button_frame, width=1200, height=800, corner_radius = 10, border_width=50, fg_color="#3D5328", border_color="#212121")
        self.border_frame.pack_propagate(0) # Restrict frame automatic resizing
        self.border_frame.pack()
        self.frame = ctk.CTkFrame(master=self.border_frame, fg_color="#3D5328", border_color="#212121")
        self.frame.grid_propagate(0) # Restrict frame automatic resizing
        self.frame.place( x=50, y=50)

        # Add textbox widget
        self.text = ctk.CTkTextbox(master=self.frame, width=1100, height=672, fg_color="#3D5328", text_color="black", scrollbar_button_color="black", font=("Courier New", 20, "bold"), state="normal", wrap="word")

        # Bind navigation key for different stages of the game
        if Settings.battle_results:
            self.root.bind_all('e', self.play.update_war_results)
            # Add a 'End battle' label
            self.close_label = ctk.CTkLabel(master=self.frame, text="'d' - for drone  'r' - for radar  'c' - for console  'e' - to end battle", fg_color="#3D5328", text_color="black", font=("Courier New", 20, "bold"))
        elif Settings.war_results and Settings.game:
            self.root.bind_all('c', self.play.play_the_game)
            # Add a 'Close' label
            self.close_label = ctk.CTkLabel(master=self.frame, text="'c' - to close report", fg_color="#3D5328", text_color="black", font=("Courier New", 20, "bold"))
        elif not Settings.game or Settings.end_war_results:
            self.root.bind('c', self.hide_text_widget)
            # Add a 'Close' label
            self.close_label = ctk.CTkLabel(master=self.frame, text="'c' - to close report", fg_color="#3D5328", text_color="black", font=("Courier New", 20, "bold"))
        else:
            # Add a 'Close' label
            self.close_label = ctk.CTkLabel(master=self.frame, text="'c' - to close report", fg_color="#3D5328", text_color="black", font=("Courier New", 20, "bold"))

        # Load text from file
        with open(filename, 'r') as file:
            content = file.read()
        self.text.insert('1.0', content)
        self.text.configure(state="disabled")

        # Pack widgets
        self.text.pack()
        self.close_label.pack()

        # Take focus on main window
        self.root.focus()

    def hide_text_widget(self, event=None):
        self.root.unbind_all('c')
        self.border_frame.pack_forget()
        self.show_menu('main')

    def display_rules(self):
        self.display_txt_file(os.path.join(os.getcwd(), 'rules.txt'))

    def display_about(self):
        self.display_txt_file(os.path.join(os.getcwd(), 'about.txt'))

    def ask_quit(self, event=None):
        """The function to quit the game entirely"""
        
        current_topmost_window = None

        if hasattr(self, 'root') and self.root.winfo_ismapped() and self.root.attributes('-topmost'):
            current_topmost_window = self.root

        # Check if there are other windows on top (-topmost, 1) to hide message box
        if hasattr(self, 'play'):
            if (hasattr(self.play, 'map_drone') and 
                hasattr(self.play.map_drone, 'map_window') and
                self.play.map_drone.map_window.winfo_exists() and
                self.play.map_drone.map_window.winfo_ismapped() and
                self.play.map_drone.map_window.attributes('-topmost')):
                current_topmost_window = self.play.map_drone.map_window

            if (hasattr(self.play, 'radar') and 
                hasattr(self.play.radar, 'radar_window') and
                self.play.radar.radar_window.winfo_exists() and
                self.play.radar.radar_window.winfo_ismapped() and
                self.play.radar.radar_window.attributes('-topmost')):
                current_topmost_window = self.play.radar.radar_window

            if (hasattr(self.play, 'console') and 
                hasattr(self.play.console, 'console') and
                self.play.console.console.winfo_exists() and
                self.play.console.console.winfo_ismapped() and
                self.play.console.console.attributes('-topmost')):
                current_topmost_window = self.play.console.console

        answer = messagebox.askyesno("Quit", "Do you really want to quit the game? You will lose all your game progress.", parent=current_topmost_window, default=messagebox.NO)
        
        if answer:
            self.root.quit()

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    game = Game()
    game.run()
