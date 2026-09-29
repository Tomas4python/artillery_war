"""The commander's field console: weather, situation report, firing inputs and unit status."""

import tkinter as tk

from artillery_war.config import AZIMUTH_RANGE, CHARGE_RANGE, ELEVATION_RANGE
from artillery_war.core.battle import FiringOrder
from artillery_war.ui import theme
from artillery_war.ui.tablet import TabletWindow

READY = 'Ready for shot'


def _label(parent, text=None, **kwargs):
    return tk.Label(parent, text=text, bg=theme.KHAKI, font=theme.CONSOLE_FONT, **kwargs)


def _format_input(value):
    if not value:
        return 'N/A'
    try:
        return f'{float(value)}'
    except ValueError:
        return value


def _frame_title(frame, title):
    frame.configure(text=title, bg=theme.KHAKI, labelanchor='nw', bd=1, relief='solid', font=theme.FRAME_TITLE_FONT)


class Console(TabletWindow):
    """The field console: a borderless tablet window, dragged by its bezel."""

    def __init__(self, root, position, on_moved=None):
        super().__init__(root, position, on_moved, title='Field console')
        self.console = self.window  # the name the rest of the game uses for this window

        navigation_info = (
            "'d' - for drone  'r' - for radar  'c' - for console  'w' - for withdraw  's' - for statistics"
        )
        tk.Label(
            self.main_frame,
            text=navigation_info,
            bg=theme.KHAKI,
            anchor='nw',
            bd=0,
            relief='solid',
            font=theme.CONSOLE_FONT,
        ).grid(row=3, column=0, columnspan=4, padx=10, pady=10)


class WeatherConditions(tk.LabelFrame):
    """The battle's weather, one labeled row per value."""

    def __init__(self, parent, weather_report, **kwargs):
        super().__init__(parent, **kwargs)
        _frame_title(self, 'Weather Conditions')
        self.grid(row=0, column=0, padx=10, pady=10)
        for index, (label_text, value) in enumerate(weather_report.items()):
            _label(self, label_text).grid(row=index, column=0, sticky='w', padx=10)
            _label(self, value).grid(row=index, sticky='e', column=1, padx=10)


class SituationReport(tk.LabelFrame):
    """Scrolling log of what happens on the battlefield."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        _frame_title(self, 'Situation Report')
        self.grid(row=0, column=1, columnspan=3, sticky='nsew', padx=10, pady=10)
        self.report_area = tk.Text(
            self,
            bg=theme.KHAKI,
            fg=theme.TEXT,
            font=theme.CONSOLE_FONT,
            cursor='double_arrow',
            relief='flat',
            height=7,
            width=60,
            wrap='word',
        )
        self.report_area.pack()
        self.report_area.configure(state='disabled')

    def insert_message(self, report_message):
        self.report_area.configure(state='normal')
        self.report_area.insert('end', '\n' + report_message)
        self.report_area.configure(state='disabled')
        self.report_area.see('end')


class ShotParameterInput(tk.LabelFrame):
    """Azimuth / elevation / charge entries for each of the player's guns, and the fire controls."""

    def __init__(self, parent, situation_report, controller, player_units, **kwargs):
        super().__init__(parent, **kwargs)
        self.situation_report = situation_report
        self.controller = controller
        self.guns = [u for u in player_units if u.is_artillery]
        # Per gun: StringVars for (azimuth, elevation, charge). They start empty.
        self.inputs = {gun.unit_number: (tk.StringVar(), tk.StringVar(), tk.StringVar()) for gun in self.guns}
        self.inputs_copy = {}
        self.make_copy_of_inputs()

        _frame_title(self, 'Shot Parameter Input')
        self.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=10, pady=10)
        for column in range(1, 4):
            self.master.grid_columnconfigure(column, weight=1)

        _label(self, 'AZIMUTH\n(0.0-±360.0)').grid(row=1, column=0, sticky='w', padx=10)
        _label(self, 'ELEVATION\n(15.0-75.0)').grid(row=2, sticky='w', column=0, padx=10)
        _label(self, '  CHARGES\n  (1-5)').grid(row=3, sticky='w', column=0, padx=10)

        self.entry_widgets = []  # (entry, gun)
        for gun in self.guns:
            column = gun.unit_number
            _label(self, f'UNIT {gun.unit_number}').grid(row=0, column=column, sticky='ew', padx=10)
            for row, variable in enumerate(self.inputs[gun.unit_number], start=1):
                entry = tk.Entry(
                    self,
                    textvariable=variable,
                    bg=theme.KHAKI_LIGHT,
                    selectbackground=theme.KHAKI,
                    selectforeground=theme.TEXT,
                    font=theme.CONSOLE_FONT,
                    width=6,
                    bd=0,
                    justify='right',
                    relief='solid',
                    cursor='xterm',
                    readonlybackground=theme.KHAKI,
                )
                entry.grid(row=row, column=column, padx=10)
                self.entry_widgets.append((entry, gun))
            self.grid_columnconfigure(column, weight=1)

        frame_for_buttons = tk.Frame(self, bg=theme.KHAKI)
        frame_for_buttons.grid(row=4, column=0, columnspan=len(self.guns) + 1, padx=10, pady=10)

        buttons = {
            'SHOW INITIAL': ('normal', self.show_previous),
            'RESET': ('normal', self.reset_to_previous),
            'CONFIRM': ('normal', self.confirm),
            'FIRE': ('disabled', self.fire),
        }
        self.buttons = {}
        for index, (text, (state, command)) in enumerate(buttons.items()):
            button = tk.Button(
                frame_for_buttons,
                text=text,
                bg=theme.KHAKI,
                bd=1,
                cursor='hand2',
                command=command,
                font=theme.CONSOLE_FONT,
                width=20,
                relief='flat',
                state=state,
                activebackground=theme.KHAKI_LIGHT,
                disabledforeground=theme.KHAKI,
                overrelief='solid',
            )
            button.grid(row=0, column=index, padx=10)
            self.buttons[text] = button

    def make_copy_of_inputs(self):
        """Remember the current inputs so RESET can restore them."""
        self.inputs_copy = {number: tuple(v.get() for v in variables) for number, variables in self.inputs.items()}

    def show_previous(self):
        """Print the remembered inputs to the situation report."""
        header = ['    ']
        rows = ([], [], [])
        for gun in self.guns:
            header.append(f'Unt{gun.unit_number}')
            for row, value in zip(rows, self.inputs_copy[gun.unit_number], strict=True):
                row.append(_format_input(value))

        spaces = ' ' * (27 - int(len(self.guns) * 2 * 3 / 2))  # center the table
        report_message = 'Showing initial shot parameters:\n'
        report_message += spaces + ' '.join(f'{label:>5}' for label in header) + '\n'
        for title, row in zip(('AZMT: ', 'ELVT: ', 'CHRG: '), rows, strict=True):
            report_message += spaces + title + ' '.join(f'{value:>5}' for value in row) + '\n'
        self.situation_report.insert_message(report_message)

    def reset_to_previous(self):
        """Unlock the entries and restore the remembered inputs; guns out of action get neutral values."""
        for entry, gun in self.entry_widgets:
            if gun.is_active:
                entry.config(state='normal')
        for gun in self.guns:
            values = self.inputs_copy[gun.unit_number] if gun.is_active else ('0.0', '15.0', '1')
            for variable, value in zip(self.inputs[gun.unit_number], values, strict=True):
                variable.set(value)
        self.buttons['FIRE'].config(state='disabled')
        self.buttons['CONFIRM'].config(state='normal')

    def confirm(self):
        """Validate the inputs and, if they are fine, lock them and enable FIRE."""
        message = self.validate_input()
        self.situation_report.insert_message(message)
        if message == READY:
            for entry, _gun in self.entry_widgets:
                entry.config(state='readonly')
            self.buttons['FIRE'].config(state='normal')
            self.buttons['CONFIRM'].config(state='disabled')

    def validate_input(self):
        """'Ready for shot', or one error line per invalid input."""
        error_messages = []
        for gun in self.guns:
            n = gun.unit_number
            try:
                order = self._parse(n)
            except ValueError:
                error_messages.append(f'The specified parameters of unit {n} are not valid.')
                continue
            if not (AZIMUTH_RANGE[0] <= order.azimuth <= AZIMUTH_RANGE[1]):
                error_messages.append(f'The specified azimuth of unit {n} is not valid.')
            if not (ELEVATION_RANGE[0] <= order.elevation <= ELEVATION_RANGE[1]):
                error_messages.append(f'The specified elevation of unit {n} is not valid.')
            if not (CHARGE_RANGE[0] <= order.charge <= CHARGE_RANGE[1]):
                error_messages.append(f'The specified charge of unit {n} is not valid.')
        return '\n'.join(error_messages) if error_messages else READY

    def _parse(self, unit_number):
        azimuth, elevation, charge = (v.get() for v in self.inputs[unit_number])
        return FiringOrder(float(azimuth), float(elevation), int(charge))

    def orders(self):
        """Validated firing orders for all guns, keyed by unit number."""
        return {gun.unit_number: self._parse(gun.unit_number) for gun in self.guns}

    def disable(self):
        for name in ('FIRE', 'CONFIRM', 'RESET'):
            self.buttons[name].config(state='disabled')

    def fire(self):
        self.controller.make_turn()


class UnitStatus(tk.LabelFrame):
    """Damage to each gun and shells left in each truck."""

    def __init__(self, parent, player_units, **kwargs):
        super().__init__(parent, **kwargs)
        self.player_units = player_units
        self.values = {id(u): tk.IntVar() for u in player_units}
        self.refresh()

        _frame_title(self, 'Unit Status')
        self.grid(row=2, column=0, columnspan=4, sticky='nsew', padx=10, pady=10)
        _label(self, 'DAMAGE,(%)').grid(row=2, column=0, sticky='w', padx=10)
        _label(self, 'AMMO,(pcs)').grid(row=4, sticky='w', column=0, padx=10)

        for unit in player_units:
            column = unit.unit_number
            value = tk.Label(self, textvariable=self.values[id(unit)], bg=theme.KHAKI, font=theme.CONSOLE_FONT)
            if unit.is_artillery:
                _label(self, f'UNIT {unit.unit_number}').grid(row=0, column=column, sticky='nsew', padx=10)
                _label(self, unit.name).grid(row=1, column=column, sticky='nsew', padx=10)
                value.grid(row=2, sticky='nsew', column=column, padx=10)
                self.grid_columnconfigure(column, weight=1)
            else:
                _label(self, unit.name).grid(row=3, column=column, sticky='nsew', padx=10)
                value.grid(row=4, sticky='nsew', column=column, padx=10)

    def refresh(self):
        """Copy the units' current damage and ammo into the labels."""
        for unit in self.player_units:
            self.values[id(unit)].set(unit.damage if unit.is_artillery else unit.ammo)
