"""Linux: real X input (xdotool) into the borderless console, plus window stacking checks."""

import os
import subprocess
import sys
import traceback

sys.path.insert(0, os.environ.get('REPO', '/app'))
from PIL import ImageGrab  # noqa: E402

from artillery_war.ui import theme  # noqa: E402
from artillery_war.ui.app import App  # noqa: E402

OUT = sys.argv[1]
results = {}


def log(*a):
    print(*a, flush=True)


def xdo(*args):
    subprocess.run(['xdotool', *args], check=True)


app = App()
c = app.controller
app.root.report_callback_exception = lambda exc, value, tb: log(''.join(traceback.format_exception(exc, value, tb)))
log('screen', app.screen_width, app.screen_height, '| fonts:', theme.MONO, '/', theme.SANS)
log('sound enabled:', c.sound_manager.enabled)


def later(ms, fn):
    def run():
        # A test driver: log any failure and stop.
        # noinspection PyBroadException
        try:
            fn()
        except Exception:
            log(traceback.format_exc())
            app.root.quit()

    app.root.after(ms, run)


def shot(name):
    app.root.update()
    ImageGrab.grab(xdisplay=os.environ['DISPLAY']).save(f'{OUT}/linux_{name}.png')


def s1():
    shot('01_welcome')
    app.show_menu('main')
    later(800, s1b)


def s1b():
    shot('02_menu')
    c.play_the_game()
    later(2500, s2)


def s2():
    shot('03_battle_start')
    results['console hidden while report shown'] = not c.console.console.winfo_ismapped()
    xdo('key', 'c')  # real key press -> raise_console via bind_all
    later(800, s3)


def s3():
    results['c raises console'] = c.console.console.winfo_ismapped()
    shot('04_console')
    entry = c.shot_parameter_input.entry_widgets[0][0]
    x = entry.winfo_rootx() + entry.winfo_width() // 2
    y = entry.winfo_rooty() + entry.winfo_height() // 2
    xdo('mousemove', str(x), str(y), 'click', '1')
    later(300, s4)


def s4():
    xdo('type', '--delay', '50', '7.5')
    later(600, s5)


def s5():
    results['typed azimuth'] = c.shot_parameter_input.inputs[1][0].get()
    # Fill the rest programmatically and fire one turn.
    for az, el, ch in c.shot_parameter_input.inputs.values():
        if not az.get():
            az.set('5.0')
        el.set('45.0')
        ch.set('3')
    c.shot_parameter_input.confirm()
    c.shot_parameter_input.fire()
    later(800, s6)


def s6():
    shot('05_after_turn')
    xdo('key', 'r')
    later(800, s7)


def s7():
    results['r hides console'] = not c.console.console.winfo_ismapped()
    shot('06_radar')
    # Mouse wheel over the radar (X11 buttons 4/5).
    before = c.radar.canvas.yview()[0]
    xdo('mousemove', '960', '540', 'click', '4', 'click', '4')
    later(400, lambda: s8(before))


def s8(before):
    results['wheel scrolls radar'] = c.radar.canvas.yview()[0] < before
    xdo('key', 'd' if c.map_drone else 'c')
    later(800, s9)


def s9():
    shot('07_drone')
    xdo('key', 'c')
    later(500, s10)


def s10():
    xdo('key', 'w')
    later(500, s11)


def s11():
    text = c.situation_report.report_area.get('1.0', 'end')
    results['w asks to withdraw'] = 'y/n?' in text
    xdo('key', 'y')
    later(8000, s12)  # 3 s to read, then 4 s console before the report


def s12():
    shot('08_battle_report')
    results['battle report shown'] = c.stage.battle_results
    xdo('key', 'e')
    later(1000, s13)


def s13():
    shot('09_war_report')
    results['war report after e'] = c.stage.war_results
    app.root.quit()


later(1500, s1)
app.root.after(60000, app.root.quit)
app.run()
for k, v in results.items():
    log(f'{k}: {v}')
