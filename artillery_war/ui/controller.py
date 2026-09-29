"""Connects the game core to the windows: runs battles and shows the reports.

Flow of a war::

    play_the_game ─> (first call) new Campaign, initial war report
        └─> new battle: console, statistics tablet, drone map (defender), radar
              └─> FIRE ─> make_turn ─> ... ─> BattleOver ─> battle report (floating tablet)
                    └─> 'e' ─> update_war_results ─> war report
                          └─> 'c' ─> play_the_game (next battle or end of war)
"""

import dataclasses
import random

import customtkinter as ctk

from artillery_war import platform_utils
from artillery_war.audio import SoundManager
from artillery_war.config import DEFENDER, INTRUDER
from artillery_war.core.campaign import Campaign
from artillery_war.core.events import BattleOver, Blasts, Message, Sound
from artillery_war.ui import theme
from artillery_war.ui.console import Console, ShotParameterInput, SituationReport, UnitStatus, WeatherConditions
from artillery_war.ui.map_view import MapView
from artillery_war.ui.radar_view import RadarView
from artillery_war.ui.report import ReportWindow
from artillery_war.ui.tablet import default_tablet_position

NAVIGATION_KEYS = ('e', 'd', 'r', 'c', 's', 'w')
BATTLE_REPORT_HINT = "'d' - for drone  'r' - for radar  'c' - for console"
END_OF_BATTLE_HINT = BATTLE_REPORT_HINT + "  'e' - to end battle"

DRONE_EXCUSES = (
    'Your drone was sold by your commander to the enemy.',
    'Your drone has not reached the battlefield.',
    "You sold parts of the drone, now it's missing the camera.",
    'Your drone has been handed over to a private military group.',
    "You've never had a drone.",
    'Your general took the drone to his villa by the sea.',
    "I don't understand, what are these 'drones'?",
    "Your general's son is now playing with a drone at home.",
    'Yesterday the military command promised that the drones will reach you tomorrow.',
    "What do you mean by 'drone'?",
    'Drone is in the air, but lost control and video.',
    'The drone failed to launch.',
    'The drone took off successfully and crashed.',
    'Yesterday you stepped on the wing of the drone.',
    "The drone's batteries are dead.",
    "You used drone's fuel to warm you up on a cold night.",
)


@dataclasses.dataclass
class GameStage:
    """Which screen the game is on; the main window uses it to pick key bindings."""

    game: bool = False  # a war is in progress
    battle_results: bool = False  # a battle has just ended
    war_results: bool = False  # the war report after a battle is showing
    end_war_results: bool = False  # the war is over


class GameController:
    """Runs a war in the windows: opens battles, replays turns, shows the reports."""

    def __init__(self, app):
        self.app = app
        self.stage = GameStage()
        self.sound_manager = SoundManager()
        # Cosmetic randomness (radar jitter, drone excuses) is kept apart from the game's RNG.
        self.ui_rng = random.Random()
        self.campaign = None
        self.battle = None
        self.map_drone = None
        self.radar = None
        self.console = None
        self.report_window = None  # statistics tablet during a battle ('s')
        self.tablet_position = None  # where the player put the tablet this battle; shared by both tablets
        self._raised = None  # the game window currently on top
        self.replaying = False  # a turn's events are still being played out
        # Widgets of the current battle, created by play_the_game.
        self.battle_no_label = self.situation_report = self.shot_parameter_input = self.unit_status = None
        self.drone_excuse = ''

    @property
    def options(self):
        return self.campaign.options

    @property
    def root(self):
        return self.app.root

    # ------------------------------------------------------------- battles

    def play_the_game(self, _event=None):
        """Start a war if none is running, then the next battle (or the end of the war)."""
        if not self.stage.game:
            # Options are fixed for the whole war.
            self.campaign = Campaign(dataclasses.replace(self.app.options), random.Random())
            self.stage.game = True
            self.stage.war_results = False
            self.stage.end_war_results = False
            self.show_war_results()

        if self.campaign.should_end():
            self.show_war_end_results()
            return

        war_report = self._war_report_text()  # as it stands before this battle, like the main window shows
        self.battle = battle = self.campaign.new_battle()
        role = self.options.player_role
        self.root.attributes('-topmost', 1)
        self._raised = self.root

        self.battle_no_label = ctk.CTkLabel(
            master=self.root,
            text='ENTER THE',
            fg_color=theme.KHAKI,
            text_color=theme.TEXT,
            font=theme.BATTLE_LABEL_FONT,
            padx=15,
        )
        self.battle_no_label.place(relx=0.5, rely=0.04, anchor='center')

        if self.tablet_position is None:
            self.tablet_position = default_tablet_position(self.app.screen_width, self.app.screen_height)
        self.console = Console(self.root, self.tablet_position, self._tablet_moved)
        WeatherConditions(self.console.main_frame, battle.weather.as_report())
        self.situation_report = SituationReport(self.console.main_frame)
        self.situation_report.insert_message(f'             {self.options.call_sign}, WELCOME!')
        self.shot_parameter_input = ShotParameterInput(
            self.console.main_frame, self.situation_report, self, battle.player_units
        )
        self.unit_status = UnitStatus(self.console.main_frame, battle.player_units)
        self.situation_report.insert_message(f'      ----- ----- BATTLE #{battle.record.battle_index} ----- -----')

        if role == DEFENDER:
            self.map_drone = MapView(
                self.root, battle.map_path, (self.app.screen_width, self.app.screen_height), battle.map_size
            )
            for unit in battle.all_units:
                self.map_drone.add_unit(unit)
        else:
            self.map_drone = None

        self.radar = RadarView(
            self.root,
            battle.radar_path,
            battle.map_direction,
            battle.weather.wind_direction,
            self.situation_report,
            role,
            (self.app.screen_width, self.app.screen_height),
            self.ui_rng,
        )
        for unit in battle.all_units:
            if unit.is_artillery:
                self.radar.add_unit(unit)

        # Statistics ('s') float over the battle view on a tablet at the console's position.
        self.report_window = ReportWindow(self.root, self.tablet_position, self._tablet_moved)
        for tablet in (self.console, self.report_window):
            tablet.on_drag = self._tablet_dragging
        self.report_window.show(war_report, BATTLE_REPORT_HINT)

        # The war report on the main window stays in front until the player presses a key.
        self._raise(self.root, focus=False)

        self.battle_no_label.configure(text='')
        self._type_label_text(self.battle_no_label, f'BATTLE #{battle.record.battle_index}')

        self.root.unbind_all('c')
        if role == DEFENDER:
            self.root.bind_all('d', self.raise_map)
        else:
            # The intruder has no drone; pressing 'd' shows one excuse per battle.
            self.drone_excuse = self.ui_rng.choice(DRONE_EXCUSES)
            self.root.bind_all('d', self.message_about_drone)
        self.root.bind_all('r', self.raise_radar)
        self.root.bind_all('c', self.raise_console)
        self.root.bind_all('s', self.raise_menu)
        self.root.bind_all('w', self.withdraw)

    def _type_label_text(self, label, text, index=0):
        """Typewriter effect, one character every 50 ms."""
        if index < len(text):
            label.configure(text=label.cget('text') + text[index])
            self.sound_manager.play_sound('typing')
            label.after(50, self._type_label_text, label, text, index + 1)

    def make_turn(self):
        """FIRE: the player's guns fire with the confirmed inputs, then the computer answers."""
        if self.battle.is_over or self.replaying:
            return
        orders = self.shot_parameter_input.orders()
        self.shot_parameter_input.make_copy_of_inputs()
        self.replay(self.battle.begin_turn())
        self.shot_parameter_input.show_previous()
        fire_button = self.shot_parameter_input.buttons['FIRE']
        fire_button.config(state='disabled')  # until this turn has played out

        def turn_played():
            self.unit_status.refresh()
            if not self.battle.is_over:
                fire_button.config(state='normal')

        self.replay(self.battle.resolve_turn(orders), then=turn_played)

    def replay(self, events, then=None):
        """Show events in order: report lines, sounds, blasts, the end of the battle.

        A sound with a delay pauses the sequence for that long before it plays, as the
        game always did, but the pause is scheduled on the event loop: the windows stay
        responsive and report lines appear in step with the sounds.
        """
        self.replaying = True
        self._play_events(list(events), 0, then, waited=False)

    def _play_events(self, events, index, then, waited):
        if self.console is None or not self.console.console.winfo_exists():
            self.replaying = False  # the battle windows were closed meanwhile
            return
        while index < len(events):
            event = events[index]
            if isinstance(event, Sound):
                delay_ms = int(round(event.delay_for(self.sound_manager.length(event.name)) * 1000))
                if delay_ms and not waited:
                    self.root.after(delay_ms, self._play_events, events, index, then, True)
                    return
                self.sound_manager.play_sound(event.name)
            else:
                self._show_event(event)
            waited = False
            index += 1
        self.replaying = False
        if then is not None:
            then()

    def _show_event(self, event):
        if isinstance(event, Message):
            self.situation_report.insert_message(event.text)
        elif isinstance(event, Blasts):
            for index, blasts in enumerate((event.player, event.computer)):
                for coords in blasts:
                    if self.map_drone is not None:
                        self.map_drone.add_blast_pit(coords)
                    self.radar.add_blast_echo(index, coords)
        elif isinstance(event, BattleOver):
            self.show_battle_results()

    # ------------------------------------------------------------ windows

    def _tablet_windows(self):
        """The borderless tablets (console, statistics) of the current battle."""
        return [t.window for t in (self.console, self.report_window) if t is not None]

    def _battle_windows(self):
        windows = [self.radar.radar_window, *self._tablet_windows()]
        if self.map_drone is not None:
            windows.append(self.map_drone.map_window)
        return windows

    def _tablet_dragging(self, x, y):
        """While one tablet is dragged, the other follows at once, so it never shows from under it."""
        for tablet in (self.console, self.report_window):
            if tablet is not None and tablet.position != (x, y):
                tablet.move_to(x, y)

    def _tablet_moved(self, x, y):
        """The player dragged a tablet: console and statistics share one position."""
        self.tablet_position = (x, y)
        for tablet in (self.console, self.report_window):
            if tablet is not None and tablet.position != (x, y):
                tablet.move_to(x, y)

    def _raise(self, window, focus=True):
        """Put ``window`` on top of all game windows and (by default) focus it.

        Only the window we come from is demoted: it drops to just below the new one. So a
        tablet raised over the radar or drone view keeps that view visible behind it.
        """
        tablets = self._tablet_windows()
        if window is not self.root and self.app.report is not None:
            # The war report shown on the main window at battle start would stay behind a
            # moved tablet; during the battle the statistics tablet ('s') takes its place.
            self.app.close_report()
        previous = self._raised
        window.attributes('-topmost', 1)
        if previous is not None and previous is not window and previous.winfo_exists():
            previous.attributes('-topmost', 0)
        self._raised = window
        if platform_utils.IS_WINDOWS:
            # Both tablets stay shown (hiding and re-showing them makes Windows redraw, which
            # blinks); the one below is covered exactly and follows every drag.
            if focus and window in tablets:
                window.focus_force()  # borderless: plain focus() may leave the keyboard elsewhere
            elif focus:
                window.focus()
            return
        # Borderless tablets are outside the X11 window manager's stacking and focus handling:
        # only the raised one is shown, and it is lifted and given the focus directly.
        for tablet in tablets:
            if tablet is window:
                tablet.deiconify()
            else:
                tablet.withdraw()
        window.lift()
        if focus:
            window.focus_force()

    def raise_map(self, _event=None):
        self._raise(self.map_drone.map_window)

    def raise_menu(self, _event=None):
        """'s': the statistics tablet, over whatever view is behind it."""
        self._raise(self.report_window.window)

    def raise_radar(self, _event=None):
        self._raise(self.radar.radar_window)

    def raise_console(self, _event=None):
        self._raise(self.console.console)

    def message_about_drone(self, _event=None):
        self.raise_console()
        self.situation_report.insert_message(self.drone_excuse)

    def withdraw(self, _event=None):
        """'w': ask whether to retreat; 'y' ends the battle with all the player's units lost."""
        if self.stage.battle_results:
            self.situation_report.insert_message('\n     Moving to new positions!')
            return
        if self.replaying:
            return  # answer once this turn's shells have landed

        role = self.options.player_role
        console = self.console.console

        def on_key(key_event):
            console.unbind('<Key>', key_binding_id)
            if key_event.char == 'y':
                if role == DEFENDER:
                    self.situation_report.insert_message('\n     We pack up and retreat.')
                else:
                    self.situation_report.insert_message(
                        "\n     Let everything burn in HELL, we're getting out of here, every man for himself!"
                    )
                self.replaying = True  # no more turns while the retreat plays out
                console.after(3000, lambda: self.replay(self.battle.withdraw()))  # time to read the message
            elif role == DEFENDER:
                self.situation_report.insert_message(
                    '\nWe have no possibility to retreat from the battlefield without losing equipment, '
                    'we will make last shots and retreat.'
                )
            else:
                self.situation_report.insert_message(
                    '\nWe will heroically sacrifice our lives for the honor of the Motherland, we will fight to the last.'  # noqa: E501
                )

        self.raise_console()
        call_sign = self.options.call_sign
        if role == DEFENDER:
            self.situation_report.insert_message(
                f'\n{call_sign}, you received an order from the direct military commander to retreat. '
                'Do you still have a possibility to retreat? y/n?'
            )
        elif role == INTRUDER:
            self.situation_report.insert_message(
                f'\n{call_sign}, you received an order from the direct military commander to fight until the last '
                'drop of blood. Will you disobey orders and flee the battlefield? y/n?'
            )
        key_binding_id = console.bind('<Key>', on_key)

    # ------------------------------------------------------------ reports

    def show_battle_results(self):
        """Show the console for 4 seconds (to read the outcome), then the battle report."""
        self.stage.battle_results = True
        self.shot_parameter_input.disable()  # no more turns while the outcome is shown
        self.raise_console()
        self.console.console.after(4000, self._show_battle_report)

    def _show_battle_report(self):
        self.shot_parameter_input.disable()

        battle = self.battle
        text = f'\n                                   BATTLE REPORT Nr.{battle.record.battle_index}\n\n'
        sequence = [DEFENDER, INTRUDER] if self.options.player_role == DEFENDER else [INTRUDER, DEFENDER]
        headings = [f'\n          {self.options.call_sign}, Your stats:\n', "\n\n          Enemy's stats:\n"]
        for heading, role in zip(headings, sequence, strict=True):
            units = battle.units[role]
            guns = [u for u in units if u.is_artillery]
            trucks = [u for u in units if u.is_ammo]
            spaces = ' ' * (35 - int(len(units) * 3 / 2))  # center the table

            def row(title, values):
                return spaces + title + ' '.join(f'{v:>7}' for v in values) + '\n'  # noqa: B023

            def status(unit):
                return 'Active' if unit.is_active else 'Down'

            text += heading + '\n'
            text += spaces + ' '.join(
                f'{label:>7}' for label in ['         '] + [f'UNIT {u.unit_number}' for u in guns]
            )
            text += '\n'
            text += row('DAMAGE:   ', [str(u.damage) for u in guns])
            text += row('HOWITZER: ', [status(u) for u in guns])
            text += row('AMMO:     ', [str(u.ammo) for u in trucks])
            text += row('TRUCK:    ', [status(u) for u in trucks])
        text += battle.battle_message
        self.report_window.show(text, END_OF_BATTLE_HINT)
        self.raise_menu()
        self.root.bind_all('e', self.update_war_results)

    def update_war_results(self, _event=None):
        """'e' after a battle: close the battle windows and show the war report."""
        for key in NAVIGATION_KEYS:
            self.root.unbind_all(key)
        self.battle_no_label.place_forget()
        self.root.attributes('-topmost', 1)
        for window in self._battle_windows():
            window.destroy()
        # Drop the closed windows so their large images are freed now, not at the next battle.
        self.map_drone = self.radar = self.console = self.report_window = None
        self.tablet_position = None  # each battle starts with the tablet in the middle again
        self._raised = self.root
        # The closed tablet had the keyboard; take it back, or Windows gives it to another program.
        self.root.focus_force()

        self.campaign.absorb_battle_remains()
        self.stage.war_results = True
        self.app.close_report()
        self.show_war_results()

    def show_war_results(self):
        """War report on the main window: both sides' remaining resources and the battle score."""
        self.stage.battle_results = False
        text = self._war_report_text()
        if self.stage.end_war_results:
            text += f'\n YOUR WAR IS OVER: {self.campaign.final_message}\n'
            self.stage.game = False
        self.app.display_text(text)

    def _war_report_text(self):
        campaign = self.campaign
        record = campaign.record

        text = '\n                                       WAR REPORT\n\n'
        statistics = {
            DEFENDER: (campaign.defender_total_units, campaign.defender_total_ammo, campaign.defender_total_damage),
            INTRUDER: (campaign.intruder_total_units, campaign.intruder_total_ammo, campaign.intruder_total_damage),
        }
        sequence = [DEFENDER, INTRUDER] if self.options.player_role == DEFENDER else [INTRUDER, DEFENDER]
        headings = [f'\n          {self.options.call_sign}, Your stats:\n\n', "\n          Enemy's stats:\n\n"]
        spaces = ' ' * 33
        for heading, role in zip(headings, sequence, strict=True):
            units, ammo, damage = statistics[role]
            text += heading
            text += f'{spaces}Units left total:     {units}\n'
            text += f'{spaces}Ammo left total:      {ammo}\n'
            text += f'{spaces}Damage left total:    {damage}\n\n'

        text += f'\n          Total battles fought:          {record.battle_index}\n'
        text += f'          Battles won:                   {record.battles_won}\n'
        text += f'          Battles lost:                  {record.battles_lost}\n'
        text += f'          Tied battles:                  {record.battles_tied}\n'
        text += f'          Total territory occupied:      {record.territory_occupied}\n'
        return text

    def show_war_end_results(self):
        """Apply the final verdict and show the last war report."""
        self.campaign.finish()
        self.stage.war_results = False
        self.stage.end_war_results = True
        self.stage.game = False
        self.root.unbind_all('c')
        self.app.close_report()
        self.show_war_results()
