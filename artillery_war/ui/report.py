"""The report screen (war and battle statistics, rules, about), shown on a tablet."""

import customtkinter as ctk

from artillery_war.ui import theme
from artillery_war.ui.tablet import TabletWindow

HINT_HEIGHT = 28  # px below the text for the line of key hints


def fill_report(frame, content, hint):
    """Put ``content`` (read-only, scrollable) and a key ``hint`` line on a tablet screen ``frame``."""
    frame.pack_propagate(0)
    text = ctk.CTkTextbox(
        master=frame,
        width=int(frame.cget('width')),
        height=int(frame.cget('height')) - HINT_HEIGHT,
        fg_color=theme.KHAKI,
        text_color=theme.TEXT,
        scrollbar_button_color='black',
        font=theme.REPORT_FONT,
        state='normal',
        wrap='word',
    )
    text.insert('1.0', content)
    text.configure(state='disabled')
    hint_label = ctk.CTkLabel(
        master=frame, text=hint, fg_color=theme.KHAKI, text_color=theme.TEXT, font=theme.REPORT_FONT
    )
    text.pack()
    hint_label.pack()
    return text, hint_label


class ReportWindow(TabletWindow):
    """Statistics during a battle: a tablet window that floats over the drone or radar view."""

    def __init__(self, root, position, on_moved=None):
        super().__init__(root, position, on_moved, title='Statistics')
        self.text = self.hint_label = None

    def show(self, content, hint):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.text, self.hint_label = fill_report(self.main_frame, content, hint)
