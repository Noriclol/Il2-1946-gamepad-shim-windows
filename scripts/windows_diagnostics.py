#!/usr/bin/env python3
"""Windows diagnostic probe for the IL-2 1946 gamepad shim (Windows port).

Run this on the Windows machine that has the physical controller(s) --
and ideally IL-2 1946 -- installed. It gathers exactly the data the
project's open questions are blocked on (see
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md) and writes
everything to log.txt at the repo root. Send that file back for review.

Usage (from the repo root, after cloning):

    python -m venv venv
    venv\\Scripts\\pip install pygame pyvjoy
    venv\\Scripts\\python scripts\\windows_diagnostics.py

pygame and pyvjoy are optional -- the script degrades gracefully and
reports what it couldn't check if either isn't installed. pyvjoy also
needs the vJoy driver itself (http://vjoystick.sourceforge.net/)
installed separately; pip alone won't get you that.

This script only reads. It never writes to the registry, installs
anything, or sends real keystrokes/mouse motion to any other window --
the vJoy section's "test write" only moves the *virtual* vJoy device,
which does nothing unless some other program (e.g. IL-2) is watching it.
"""

import ctypes
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "log.txt"


class Log:
    def __init__(self, path):
        self._fh = open(path, "w", encoding="utf-8")

    def write(self, line=""):
        print(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def section(self, title):
        self.write("")
        self.write("=" * 70)
        self.write(title)
        self.write("=" * 70)

    def close(self):
        self._fh.close()


def run_section(log, title, func):
    log.section(title)
    try:
        func(log)
    except Exception as exc:  # a diagnostic must never crash on one section
        log.write(f"SECTION FAILED: {type(exc).__name__}: {exc}")


def section_environment(log):
    log.write(f"Timestamp: {datetime.now().isoformat()}")
    log.write(f"Platform: {platform.platform()}")
    log.write(f"Python: {sys.version}")
    log.write(f"Architecture: {platform.architecture()}")
    log.write(f"Is Windows: {platform.system() == 'Windows'}")
    if platform.system() != "Windows":
        log.write("WARNING: this script is meant to run on the target Windows machine.")


def section_pygame(log):
    try:
        import pygame
    except ImportError:
        log.write("SKIPPED: pygame is not installed. Run: pip install pygame")
        return

    log.write(f"pygame version: {pygame.version.ver}")
    try:
        log.write(f"SDL version: {pygame.get_sdl_version()}")
    except Exception:
        log.write("SDL version: (unavailable)")

    pygame.init()
    pygame.joystick.init()
    count = pygame.joystick.get_count()
    log.write(f"Controllers detected: {count}")
    if count == 0:
        log.write("No controllers connected -- plug one in and re-run.")
        return

    for i in range(count):
        joystick = pygame.joystick.Joystick(i)
        joystick.init()
        log.write("")
        log.write(f"--- Controller [{i}]: {joystick.get_name()} ---")
        try:
            log.write(f"GUID: {joystick.get_guid()}")
        except AttributeError:
            log.write("GUID: (not available on this pygame version)")
        log.write(f"Axes: {joystick.get_numaxes()}")
        log.write(f"Buttons: {joystick.get_numbuttons()}")
        log.write(f"Hats: {joystick.get_numhats()}")

        log.write("")
        log.write("Sampling raw axis values for 10 seconds -- slowly move both")
        log.write("sticks to their full range, and slowly pull each trigger all")
        log.write("the way in and let it back out. Triggers especially need a")
        log.write("slow, deliberate full pull -- a quick tap can miss their real")
        log.write("min/max. Take your time, the window is long on purpose:")
        _sample_axes(log, pygame, joystick, seconds=10)

        log.write("")
        log.write("Now the guided button/hat capture. Each prompt below waits up")
        log.write("to 12 seconds for you to press the named control -- take your")
        log.write("time, there's no rush between prompts.")
        _capture_button(log, pygame, joystick, "SOUTH (bottom face button, e.g. A / Cross)")
        _capture_button(log, pygame, joystick, "EAST (right face button, e.g. B / Circle)")
        _capture_button(log, pygame, joystick, "WEST (left face button, e.g. X / Square)")
        _capture_button(log, pygame, joystick, "NORTH (top face button, e.g. Y / Triangle)")
        _capture_button(log, pygame, joystick, "TL (left shoulder/bumper)")
        _capture_button(log, pygame, joystick, "TR (right shoulder/bumper)")
        _capture_dpad_direction(log, pygame, joystick, "UP", hat_value=(0, 1))
        _capture_dpad_direction(log, pygame, joystick, "DOWN", hat_value=(0, -1))
        _capture_dpad_direction(log, pygame, joystick, "LEFT", hat_value=(-1, 0))
        _capture_dpad_direction(log, pygame, joystick, "RIGHT", hat_value=(1, 0))

    pygame.joystick.quit()
    pygame.quit()


def _sample_axes(log, pygame, joystick, seconds):
    seen_min = {}
    seen_max = {}
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        pygame.event.pump()
        for axis in range(joystick.get_numaxes()):
            value = joystick.get_axis(axis)
            seen_min[axis] = min(seen_min.get(axis, value), value)
            seen_max[axis] = max(seen_max.get(axis, value), value)
        time.sleep(0.02)
    for axis in range(joystick.get_numaxes()):
        log.write(f"  axis[{axis}]: observed range {seen_min[axis]:.3f} .. {seen_max[axis]:.3f}")


def _capture_button(log, pygame, joystick, label, timeout=12):
    log.write("")
    log.write(f"Press and hold the {label} button now ({timeout}s window)...")
    deadline = time.monotonic() + timeout
    found = None
    while time.monotonic() < deadline and found is None:
        pygame.event.pump()
        for b in range(joystick.get_numbuttons()):
            if joystick.get_button(b):
                found = b
                break
        time.sleep(0.02)
    if found is None:
        log.write(f"  -> no button press detected for {label} (timed out)")
        return
    log.write(f"  -> {label} = button index {found}")
    # Wait for release so the next capture doesn't immediately re-trigger.
    while joystick.get_button(found):
        pygame.event.pump()
        time.sleep(0.02)


def _capture_dpad_direction(log, pygame, joystick, direction_label, hat_value, timeout=12):
    """Capture one D-pad direction, either as a hat (matched against the
    expected (x, y) hat_value -- SDL convention: y=1 up/y=-1 down,
    x=1 right/x=-1 left) or, on a pad with 0 hats, as a plain button
    (the same fallback res.profiles.py's dpad_button_map assumes for
    the DS4). Called once per direction (UP/DOWN/LEFT/RIGHT) so every
    one gets hardware-verified, not just UP -- see
    res/profiles.py's dpad_mapping_verified=False for why that mattered:
    res/main.py used to crash-loop on guessed DOWN/LEFT/RIGHT indices
    that didn't exist on real hardware."""
    log.write("")
    if joystick.get_numhats() > 0:
        log.write(f"Push the D-pad {direction_label} now ({timeout}s window)...")
        deadline = time.monotonic() + timeout
        found = None
        while time.monotonic() < deadline and found is None:
            pygame.event.pump()
            for h in range(joystick.get_numhats()):
                value = joystick.get_hat(h)
                if value == hat_value:
                    found = (h, value)
                    break
            time.sleep(0.02)
        if found is None:
            log.write(f"  -> no hat movement detected for {direction_label} (timed out)")
        else:
            log.write(f"  -> D-pad reports as hat index {found[0]}, {direction_label} = {found[1]}")
            # Wait for release so the next direction's capture doesn't
            # immediately re-trigger on a still-held hat.
            while joystick.get_hat(found[0]) == hat_value:
                pygame.event.pump()
                time.sleep(0.02)
        return

    log.write("This controller reports 0 hats -- its D-pad is likely exposed as")
    log.write(f"extra buttons instead. Checking buttons for D-pad {direction_label}...")
    deadline = time.monotonic() + timeout
    found = None
    while time.monotonic() < deadline and found is None:
        pygame.event.pump()
        for b in range(joystick.get_numbuttons()):
            if joystick.get_button(b):
                found = b
                break
        time.sleep(0.02)
    if found is None:
        log.write(f"  -> no button press detected for D-pad {direction_label} (timed out)")
        return
    log.write(f"  -> D-pad {direction_label} = button index {found}")
    while joystick.get_button(found):
        pygame.event.pump()
        time.sleep(0.02)


def section_vjoy(log):
    try:
        import pyvjoy
    except ImportError:
        log.write("SKIPPED: pyvjoy is not installed. Run: pip install pyvjoy")
        log.write("(Also requires the vJoy driver itself -- http://vjoystick.sourceforge.net/)")
        return

    log.write("pyvjoy is installed.")
    try:
        device = pyvjoy.VJoyDevice(1)
    except Exception as exc:
        log.write(f"FAILED to open vJoy device #1: {type(exc).__name__}: {exc}")
        log.write("This usually means the vJoy driver isn't installed, or device #1")
        log.write("hasn't been configured/enabled in vJoyConf yet.")
        return

    log.write("Opened vJoy device #1 successfully.")
    try:
        device.set_axis(pyvjoy.HID_USAGE_X, 16000)
        device.set_button(1, 1)
        time.sleep(0.2)
        device.set_button(1, 0)
        log.write("Test write (axis X + button 1 tap) succeeded.")
        log.write("(This only moved the virtual vJoy device -- harmless unless")
        log.write("something else, e.g. IL-2, currently has it bound to an axis.)")
    except Exception as exc:
        log.write(f"Test write FAILED: {type(exc).__name__}: {exc}")


def section_sendinput(log):
    if platform.system() != "Windows":
        log.write("SKIPPED: not running on Windows, ctypes.windll is unavailable.")
        return

    try:
        user32 = ctypes.windll.user32
    except AttributeError:
        log.write("FAILED: ctypes.windll.user32 unavailable.")
        return

    log.write("ctypes.windll.user32 is available.")
    try:
        layout = user32.GetKeyboardLayout(0)
        lang_id = layout & 0xFFFF
        log.write(f"Current keyboard layout handle: {layout:#010x} (language id {lang_id:#06x})")
        log.write("Swedish (se) is language id 0x041d -- compare against the value above.")
    except Exception as exc:
        log.write(f"FAILED to query keyboard layout: {type(exc).__name__}: {exc}")

    log.write("No test keystrokes or mouse motion were sent -- this section only reads.")


def section_directinput_registry(log):
    if platform.system() != "Windows":
        log.write("SKIPPED: not running on Windows.")
        return

    try:
        import winreg
    except ImportError:
        log.write("SKIPPED: winreg unavailable.")
        return

    base_path = r"System\CurrentControlSet\Control\MediaProperties\PrivateProperties\DirectInput"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path)
    except FileNotFoundError:
        log.write(f"No DirectInput registry key found at HKCU\\{base_path}")
        log.write("(Normal if DirectInput hasn't cached any device instances yet.)")
        return

    log.write(f"HKCU\\{base_path} exists. Listing VID/PID subkeys:")
    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(key, i)
        except OSError:
            break
        log.write(f"  {subkey_name}")
        i += 1
    winreg.CloseKey(key)
    log.write("")
    log.write("If a controller you're using shows up here with more than one")
    log.write("Calibration\\N slot underneath it, that's the stale-instance-cache")
    log.write("issue described in the Linux source project's docs/problem.md --")
    log.write("worth noting which controller and how many slots.")


def main():
    log = Log(LOG_PATH)
    log.write("IL-2 1946 Gamepad Shim -- Windows diagnostic probe")
    log.write(f"Log written to: {LOG_PATH}")

    run_section(log, "1. Environment", section_environment)
    run_section(log, "2. Controllers (pygame)", section_pygame)
    run_section(log, "3. vJoy / pyvjoy", section_vjoy)
    run_section(log, "4. SendInput / keyboard layout", section_sendinput)
    run_section(log, "5. DirectInput instance registry", section_directinput_registry)

    log.section("Done")
    log.write(f"Send {LOG_PATH} back for review.")
    log.close()


if __name__ == "__main__":
    main()
