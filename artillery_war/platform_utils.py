"""Operating-system specific behavior, kept in one place.

The game is developed on Windows and also runs on Linux (X11). Everything that
differs between them lives here so the rest of the code stays platform-neutral.
"""

import platform

IS_WINDOWS = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'

if IS_WINDOWS:
    import ctypes

LOGPIXELSX = 88  # GetDeviceCaps index: horizontal pixels per logical inch
_icon_images: list[object] = []  # keep window icons alive (Tk does not hold a Python reference)


def enable_dpi_awareness():
    """Windows: draw at physical pixels instead of letting the system blur-scale the window."""
    if IS_WINDOWS:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
        except (AttributeError, OSError):
            pass


def desktop_scaling():
    """Desktop scaling factor, e.g. 1.25 when Windows is set to 125%; 1.0 elsewhere."""
    if not IS_WINDOWS:
        return 1.0
    user32 = ctypes.windll.user32
    hdc = user32.GetDC(0)
    actual_dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
    user32.ReleaseDC(0, hdc)
    return round(actual_dpi / 96.0, 2)


def set_window_icon(window, ico_path):
    """Windows takes the .ico directly; X11 needs it as a PhotoImage."""
    if IS_WINDOWS:
        window.iconbitmap(str(ico_path))
        return
    from PIL import Image, ImageTk

    icon = ImageTk.PhotoImage(Image.open(ico_path))
    _icon_images.append(icon)
    window.iconphoto(True, icon)


def bind_mousewheel(widget, on_scroll):
    """Call ``on_scroll(steps)`` for wheel movement; negative steps scroll up.

    Windows and macOS send <MouseWheel> (with different ``delta`` units), X11
    sends button 4 (up) and button 5 (down).
    """
    if IS_WINDOWS or IS_MAC:

        def on_wheel(event):
            steps = int(-event.delta / 120) if IS_WINDOWS else -event.delta
            if steps:
                on_scroll(steps)

        widget.bind('<MouseWheel>', on_wheel)
    else:
        widget.bind('<Button-4>', lambda event: on_scroll(-1))
        widget.bind('<Button-5>', lambda event: on_scroll(1))
