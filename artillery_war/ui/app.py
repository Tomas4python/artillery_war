"""Main window: welcome screen, menus and the report 'tablet'."""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from artillery_war import paths, platform_utils
from artillery_war.config import DEFAULT_CALL_SIGN, DEFENDER, INTRUDER, GameOptions
from artillery_war.ui import theme
from artillery_war.ui.controller import GameController
from artillery_war.ui.report import fill_report
from artillery_war.ui.tablet import BEZEL_WIDTH, TABLET_HEIGHT, TABLET_WIDTH, Tablet

REPORT_WIDTH = TABLET_WIDTH  # same tablet as the field console
REPORT_HEIGHT = TABLET_HEIGHT


class App:
    """The full-screen main window; owns the game options and the controller."""

    def __init__(self):
        platform_utils.enable_dpi_awareness()

        # Always dark, so the welcome screen looks the same in Windows light mode.
        ctk.set_appearance_mode('dark')

        self.root = ctk.CTk()
        self.root.title('Artillery War')
        self.root.attributes('-fullscreen', True)
        platform_utils.set_window_icon(self.root, paths.ICON_ICO)
        theme.configure_fonts(self.root)
        self.root.update()
        self.root.update_idletasks()
        # Size of the full-screen window; on multi-monitor X11 the "screen" spans all monitors.
        self.screen_width = self.root.winfo_width()
        self.screen_height = self.root.winfo_height()
        if self.screen_width < 800 or self.screen_height < 600:  # window manager has not applied fullscreen yet
            self.screen_width = self.root.winfo_screenwidth()
            self.screen_height = self.root.winfo_screenheight()

        start_image = Image.open(paths.START_IMAGE)
        menu_image = Image.open(paths.MENU_IMAGE)
        self.start_image = ctk.CTkImage(light_image=start_image, dark_image=start_image, size=(1152, 720))
        self.menu_image = ctk.CTkImage(
            light_image=menu_image, dark_image=menu_image, size=(self.screen_width, self.screen_height)
        )
        # The menu picture as shown, to draw the report tablet's rounded corners over the right patch of it.
        self.menu_backdrop = menu_image.resize((self.screen_width, self.screen_height))

        self.options = GameOptions()
        self.controller = GameController(self)
        self.callsign = tk.StringVar()
        self.report = None
        # Widgets created later: menus, the call-sign form and the report screen.
        self.button_frame = self.buttons = None
        self.callsign_label = self.callsign_entry = self.callsign_button = None
        self.frame = self.text = self.close_label = None

        self.image_label = ctk.CTkLabel(master=self.root, image=self.start_image, text='')
        self.image_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.instruction_label = ctk.CTkLabel(
            master=self.root, text="Press 'Space' to continue", font=(theme.MONO, 24), text_color=theme.MUTED
        )
        self.instruction_label.place(relx=0.5, rely=0.97, anchor='center')

        self.create_menu_buttons()

        self.root.bind_all('q', self.ask_quit)
        self.root.bind('<space>', lambda event: self.show_menu('main'))

    # ---------------------------------------------------------------- menus

    def _button(self, text, command):
        return ctk.CTkButton(
            master=self.button_frame,
            text=text,
            command=command,
            corner_radius=10,
            border_width=5,
            border_spacing=5,
            fg_color=theme.KHAKI,
            hover_color=theme.KHAKI_LIGHT,
            border_color='black',
            text_color=theme.TEXT,
            font=theme.MENU_FONT,
        )

    def create_menu_buttons(self):
        """Build every menu's buttons once; ``show_menu`` packs one menu's set."""

        def goto(menu_name):
            return lambda: self.show_menu(menu_name)

        def choose(**option):
            def command():
                for name, value in option.items():
                    setattr(self.options, name, value)
                self.show_menu('settings')

            return command

        menus = {
            'main': [
                ('Play the game', self.controller.play_the_game),
                ('Settings', goto('settings')),
                ('Rules', self.display_rules),
                ('About', self.display_about),
                ('[Q]uit', self.ask_quit),
            ],
            'settings': [
                ('Callsign', self.get_callsign),
                ('Choose player', goto('player')),
                ('Difficulty', goto('difficulty')),
                ('Deployment', goto('deployment')),
                ('Back to main', goto('main')),
            ],
            'player': [('Defender', choose(player_role=DEFENDER)), ('Invader', choose(player_role=INTRUDER))],
            'difficulty': [
                ('Easy', choose(level='easy')),
                ('Medium', choose(level='medium')),
                ('Hard', choose(level='hard')),
            ],
            'deployment': [('Inline', choose(deployment='inline')), ('Random', choose(deployment='random'))],
        }

        self.button_frame = ctk.CTkFrame(master=self.root, fg_color=theme.KHAKI_LIGHT)
        self.button_frame.place(relx=0.5, rely=0.5, anchor='center')
        self.button_frame.lower()  # hidden under the welcome image until a menu is shown
        self.buttons = {name: [self._button(text, command) for text, command in items] for name, items in menus.items()}

    def show_menu(self, menu_name):
        """Show the menu picture with the buttons of ``menu_name``."""
        self.root.unbind('<space>')
        self.image_label.configure(image=self.menu_image)
        self.instruction_label.place_forget()
        self.button_frame.lift()
        self.hide_all_buttons()
        for button in self.buttons[menu_name]:
            button.pack(padx=0, pady=0, fill='x')

    def hide_all_buttons(self):
        for button_list in self.buttons.values():
            for button in button_list:
                button.pack_forget()

    def get_callsign(self):
        """Replace the settings menu with a call-sign entry."""
        self.hide_all_buttons()
        self.callsign_label = ctk.CTkLabel(
            master=self.button_frame,
            text=' At least 2 characters: ',
            corner_radius=0,
            fg_color=theme.KHAKI,
            text_color=theme.TEXT,
            font=theme.MENU_FONT,
        )
        self.callsign.set(self.options.call_sign)
        self.callsign_entry = ctk.CTkEntry(
            master=self.button_frame,
            textvariable=self.callsign,
            justify='center',
            corner_radius=0,
            fg_color=theme.KHAKI_LIGHT,
            text_color=theme.TEXT,
            placeholder_text='',
            font=(theme.MONO, 40, 'bold'),
        )
        self.callsign_entry.focus()
        self.callsign_button = self._button(' Set your callsign ', self.set_callsign)
        for widget in (self.callsign_label, self.callsign_entry, self.callsign_button):
            widget.pack(padx=0, pady=0, fill='x')

    def set_callsign(self):
        """Keep the entered call sign (at least 2 characters) and return to settings."""
        callsign = self.callsign.get()
        self.options.call_sign = callsign if len(callsign) > 1 else DEFAULT_CALL_SIGN
        for widget in (self.callsign_label, self.callsign_entry, self.callsign_button):
            widget.pack_forget()
        self.show_menu('settings')

    # --------------------------------------------------------------- reports

    def display_text(self, content):
        """Show ``content`` on the report tablet and bind the key that closes it for this stage."""
        stage = self.controller.stage
        self.hide_all_buttons()

        self.button_frame.lower()
        self.close_report()

        # Where the player put the tablet in battle (so the next console opens exactly over it), else centered.
        x, y = self.controller.tablet_position or (
            (self.screen_width - REPORT_WIDTH) // 2,
            (self.screen_height - REPORT_HEIGHT) // 2,
        )
        backdrop = self.menu_backdrop.crop((x, y, x + REPORT_WIDTH, y + REPORT_HEIGHT))
        self.report = Tablet(self.root, REPORT_WIDTH, REPORT_HEIGHT, background=backdrop)
        self.report.place(x=x, y=y)
        screen_width, screen_height = self.report.screen_size
        self.frame = tk.Frame(self.report, width=screen_width, height=screen_height, bg=theme.KHAKI)
        self.frame.place(x=BEZEL_WIDTH, y=BEZEL_WIDTH)

        # Battle reports float over the battle view (controller.report_window); this screen is for the
        # war report between battles, and for rules and about.
        if stage.war_results and stage.game:
            self.root.bind_all('c', self.controller.play_the_game)
        elif not stage.game or stage.end_war_results:
            # bind_all, like every game key: hide_text_widget removes it with unbind_all. A window-level
            # root.bind would survive that and hijack 'c' in the next battle.
            self.root.bind_all('c', self.hide_text_widget)
        self.text, self.close_label = fill_report(self.frame, content, "'c' - to close report")
        self.root.focus()

    def close_report(self):
        """Remove the report tablet, if one is shown."""
        if self.report is not None:
            self.report.destroy()
            self.report = None

    def hide_text_widget(self, _event=None):
        """'c' on a report outside a war: back to the main menu."""
        self.root.unbind_all('c')
        self.close_report()
        self.show_menu('main')

    def display_rules(self):
        self.display_text(paths.RULES_TEXT.read_text(encoding='utf-8'))

    def display_about(self):
        self.display_text(paths.ABOUT_TEXT.read_text(encoding='utf-8'))

    def ask_quit(self, _event=None):
        """Ask before quitting; the dialog is parented to whichever game window is on top."""
        parent = None
        if self.root.winfo_ismapped() and self.root.attributes('-topmost'):
            parent = self.root

        c = self.controller
        candidates = [
            c.map_drone.map_window if c.map_drone else None,
            c.radar.radar_window if c.radar else None,
            c.console.console if c.console else None,
            c.report_window.window if c.report_window else None,
        ]
        for window in candidates:
            if (
                window is not None
                and window.winfo_exists()
                and window.winfo_ismapped()
                and window.attributes('-topmost')
            ):
                parent = window

        answer = messagebox.askyesno(
            'Quit',
            'Do you really want to quit the game? You will lose all your game progress.',
            parent=parent,
            default='no',
        )
        if answer:
            self.root.quit()

    def run(self):
        self.root.mainloop()
