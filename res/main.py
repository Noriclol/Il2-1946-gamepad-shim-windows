"""Entry point: wires the boot-time controller picker, axis passthrough,
rudder fold, right-stick mouse-look, and verified face/shoulder buttons
onto two vJoy devices (a gamepad (#1) and a separate rudder-only device
(#2), see res.vjoy_output for why the rudder is split off) plus SendInput
mouse motion (res.sendinput_output -- no virtual mouse device, see that
module's docstring for why).

Deliberately minimal first pass. Keyboard-macro combos are NOT wired
here -- they need D-pad-driven directions that the verified DS4 profile
can't supply (that pad reports 0 hats, see res/profiles.py), and the
keyboard side of res/sendinput_output.py isn't built yet (see
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md). This lets a
DS4 drive vJoy's X/Y/rudder axes, the four face buttons + TL/TR, and
mouse-look via the right stick, so a Windows tester can confirm the
pipeline actually moves real vJoy devices and the mouse cursor.

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

from res.config import load_last_choice, save_last_choice
from res.device_scan import NoProfileError, choose_controller, enumerate_controllers
from res.mouse_look import MouseLookState, stick_to_velocity
from res.profiles import AXIS_LT, AXIS_RT, AXIS_RX, AXIS_RY, AXIS_X, AXIS_Y
from res.rudder import fold_rudder
from res.sendinput_output import mouse_tick_loop
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


def run(joystick, profile, output, rudder_output, mouse_state):
    """Read one frame from joystick and push it onto output/rudder_output/
    mouse_state. Split out from main() so the per-frame logic is
    unit-testable without pygame or a real vJoy device -- pass any
    objects with the same shape."""
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
        output.set_button(role, bool(joystick.get_button(button_index)))


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

    print(
        f"Driving vJoy devices #1/#2 and mouse-look from {chosen.name!r}. "
        "Press Ctrl+C to stop."
    )
    try:
        while True:
            pygame.event.pump()
            run(joystick, chosen.profile, output, rudder_output, mouse_state)
            time.sleep(1 / TICK_HZ)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        mouse_stop.set()
        mouse_thread.join(timeout=1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
