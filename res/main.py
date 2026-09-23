"""Entry point: wires the boot-time controller picker, axis passthrough,
rudder fold, right-stick mouse-look, and verified face/shoulder buttons
onto two vJoy devices (a gamepad (#1) and a separate rudder-only device
(#2), see res.vjoy_output for why the rudder is split off) plus SendInput
mouse motion (res.sendinput_output -- no virtual mouse device, see that
module's docstring for why).

Also wires res.combo_detector.ComboDetector's 36 chorded macros (16
TABLE_1 button->D-pad, 16 TABLE_2 D-pad->button, 4 TABLE_3
button+TL+TR) onto PROFILE_DS4's dpad_button_map and
res.sendinput_output's scancode-based keyboard tap. The D-pad half
(TABLE_1/TABLE_2) rides on PROFILE_DS4.dpad_button_map's guessed,
not-yet-hardware-verified DOWN/LEFT/RIGHT indices (see
res/profiles.py) -- only D-pad UP is confirmed against real hardware,
so those three combos' correctness on a real pad is unverified until
someone runs scripts/windows_diagnostics.py and reports back.

This lets a DS4 drive vJoy's X/Y/rudder axes, the four face buttons +
TL/TR, mouse-look via the right stick, and the chorded macros above, so
a Windows tester can confirm the pipeline actually moves real vJoy
devices, the mouse cursor, and fires keyboard macros.

Requires vJoy already configured via vJoyConf, one time, ahead of
running this: device #1 with axes X, Y and at least 6 buttons
(res.vjoy_output.VJOY_BUTTON_MAP); device #2 with a single axis and no
buttons.

Not covered by this project's unit tests, same reasoning as
res.vjoy_output.build_vjoy_device: there's nothing to verify without a
real controller, a real vJoy driver, and a real event loop running.
"""

import os
import sys
import threading
import time

from res.combo_detector import GAMEPAD, KEYBOARD, ComboDetector
from res.config import load_last_choice, save_last_choice
from res.device_scan import NoProfileError, choose_controller, enumerate_controllers
from res.logical_input import FACE_BUTTONS, TL, TR
from res.mouse_look import MouseLookState, stick_to_velocity
from res.profiles import AXIS_LT, AXIS_RT, AXIS_RX, AXIS_RY, AXIS_X, AXIS_Y
from res.rudder import fold_rudder
from res.sendinput_output import SCANCODE_MAP, mouse_tick_loop, tap_scancode_key
from res.vjoy_output import (
    GAMEPAD_VJOY_DEVICE_ID,
    RUDDER_VJOY_DEVICE_ID,
    VJOY_BUTTON_MAP,
    GamepadOutput,
    RudderOutput,
    build_vjoy_device,
)

CONFIG_PATH = os.path.join(
    os.environ.get("APPDATA", "."), "IL2Shim", "config.json"
)

# Standard SDL joystick axis range.
STICK_MIN, STICK_MAX = -1.0, 1.0
TRIGGER_MIN, TRIGGER_MAX = -1.0, 1.0

TICK_HZ = 60.0
VJOY_AXIS_MAX = 32767


def axis_to_vjoy(value, info_min=STICK_MIN, info_max=STICK_MAX):
    """Map a pygame axis value onto vJoy's 0..VJOY_AXIS_MAX range."""
    normalized = (value - info_min) / (info_max - info_min)
    return max(0, min(VJOY_AXIS_MAX, int(normalized * VJOY_AXIS_MAX)))


class EdgeTracker:
    """Remembers the last-seen pressed state per role/direction so run()
    can feed ComboDetector actual press/release transitions.
    ComboDetector fires unconditionally whenever it's called with
    pressed=True (see its tests) -- it has no notion of "already
    pressed", since the Linux source project it's ported from only ever
    called it on real evdev press/release events. Polled pygame input
    has no such edges built in: get_button() returns the current level
    every frame, so without this, a held combo would refire every tick
    at TICK_HZ instead of once per press."""

    def __init__(self):
        self._last = {}

    def changed(self, key, pressed):
        previous = self._last.get(key, False)
        self._last[key] = pressed
        return pressed != previous


def dispatch_fire(fire, output):
    """Turn a res.combo_detector.Fire into a real side effect: a
    background-threaded keyboard tap (res.sendinput_output) for a
    KEYBOARD fire, or a background-threaded vJoy button tap for a
    GAMEPAD fire (TABLE_3's self-mapped face buttons). Threaded so
    run()'s fixed-rate poll loop never blocks for a key/button hold."""
    if fire.device == KEYBOARD:
        scancode = SCANCODE_MAP.get(fire.code)
        if scancode is not None:
            threading.Thread(target=tap_scancode_key, args=(scancode,), daemon=True).start()
    elif fire.device == GAMEPAD:
        threading.Thread(target=_tap_vjoy_button, args=(output, fire.code), daemon=True).start()


def _tap_vjoy_button(output, role, hold_seconds=0.05):
    output.set_button(role, True)
    time.sleep(hold_seconds)
    output.set_button(role, False)


def run(
    joystick,
    profile,
    output,
    rudder_output,
    mouse_state,
    combo_detector=None,
    edge_tracker=None,
    dispatch_fire=dispatch_fire,
):
    """Read one frame from joystick and push it onto output/rudder_output/
    mouse_state. Split out from main() so the per-frame logic is
    unit-testable without pygame or a real vJoy device -- pass any
    objects with the same shape.

    combo_detector/edge_tracker are optional (default None skips combo
    processing entirely, e.g. for a profile with no dpad_button_map or
    unverified buttons) -- when both are given, face buttons, D-pad
    directions (from profile.dpad_button_map), and TL/TR shoulders are
    fed to combo_detector on each press/release edge, and any resulting
    Fires are handed to dispatch_fire."""
    x = joystick.get_axis(profile.axis_map[AXIS_X])
    y = joystick.get_axis(profile.axis_map[AXIS_Y])
    lt = joystick.get_axis(profile.axis_map[AXIS_LT])
    rt = joystick.get_axis(profile.axis_map[AXIS_RT])
    rx = joystick.get_axis(profile.axis_map[AXIS_RX])
    ry = joystick.get_axis(profile.axis_map[AXIS_RY])

    output.set_x(axis_to_vjoy(x))
    output.set_y(axis_to_vjoy(y))
    rudder_output.set_rudder(
        fold_rudder(lt, TRIGGER_MIN, TRIGGER_MAX, rt, TRIGGER_MIN, TRIGGER_MAX)
    )
    mouse_state.set(
        vx=stick_to_velocity(rx, STICK_MIN, STICK_MAX),
        vy=stick_to_velocity(ry, STICK_MIN, STICK_MAX),
    )

    for role, button_index in profile.button_map.items():
        pressed = bool(joystick.get_button(button_index))

        if role in (TL, TR) and combo_detector is not None:
            if edge_tracker.changed(role, pressed):
                fires, forward = combo_detector.on_shoulder(role, pressed)
                for fire in fires:
                    dispatch_fire(fire, output)
                if forward:
                    output.set_button(role, pressed)
            # Unchanged from last frame: leave vJoy's button state as
            # this role's last edge already left it -- no continuous
            # polling needed for a discrete button.
            continue

        output.set_button(role, pressed)
        if (
            combo_detector is not None
            and role in FACE_BUTTONS
            and edge_tracker.changed(role, pressed)
        ):
            for fire in combo_detector.on_face_button(role, pressed):
                dispatch_fire(fire, output)

    if combo_detector is not None:
        for direction, button_index in profile.dpad_button_map.items():
            pressed = bool(joystick.get_button(button_index))
            if edge_tracker.changed(direction, pressed):
                for fire in combo_detector.on_dpad_direction(direction, pressed):
                    dispatch_fire(fire, output)


def open_vjoy_device(device_id, expected_shape):
    """Wrap build_vjoy_device with a message a non-technical tester can
    act on -- the raw pyvjoy exceptions (vJoyNotEnabledException,
    vJoyFailedToAcquireException, ...) don't say which device failed or
    what to do about it."""
    import pyvjoy

    try:
        return build_vjoy_device(device_id)
    except pyvjoy.vJoyException as exc:
        raise pyvjoy.vJoyException(
            f"Could not open vJoy device #{device_id} ({exc}).\n"
            f"Open vJoyConf and make sure device #{device_id} exists, is "
            f"enabled, and is configured with {expected_shape}. See the "
            f"README's 'try the shim itself' section."
        ) from exc


def main():
    import pygame

    pygame.init()
    pygame.joystick.init()

    controllers = enumerate_controllers()
    if not controllers:
        print("No controllers detected. Plug one in and try again.")
        return 1

    remembered = load_last_choice(CONFIG_PATH)
    try:
        chosen = choose_controller(controllers, remembered_name=remembered)
    except NoProfileError as exc:
        print(str(exc))
        return 1

    save_last_choice(CONFIG_PATH, chosen.name)

    joystick = pygame.joystick.Joystick(chosen.index)
    joystick.init()

    import pyvjoy

    try:
        gamepad_device = open_vjoy_device(GAMEPAD_VJOY_DEVICE_ID, "X, Y axes and at least 6 buttons")
        rudder_device = open_vjoy_device(RUDDER_VJOY_DEVICE_ID, "a single axis, no buttons")
    except pyvjoy.vJoyException as exc:
        print(str(exc))
        return 1

    output = GamepadOutput(gamepad_device, VJOY_BUTTON_MAP)
    rudder_output = RudderOutput(rudder_device)

    mouse_state = MouseLookState()
    mouse_stop = threading.Event()
    mouse_thread = threading.Thread(
        target=mouse_tick_loop, args=(mouse_state, mouse_stop), daemon=True
    )
    mouse_thread.start()

    combo_detector = ComboDetector()
    edge_tracker = EdgeTracker()

    print(
        f"Driving vJoy devices #1/#2, mouse-look, and chorded macros from "
        f"{chosen.name!r}. Press Ctrl+C to stop."
    )
    try:
        while True:
            pygame.event.pump()
            run(
                joystick,
                chosen.profile,
                output,
                rudder_output,
                mouse_state,
                combo_detector=combo_detector,
                edge_tracker=edge_tracker,
            )
            time.sleep(1 / TICK_HZ)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        mouse_stop.set()
        mouse_thread.join(timeout=1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
