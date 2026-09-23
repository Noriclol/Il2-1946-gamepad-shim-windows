"""Translate the shim's logical outputs (passthrough X/Y, buttons, folded
rudder axis) onto TWO vJoy virtual devices -- a gamepad and a separate,
single-axis rudder device.

The rudder is deliberately kept off the gamepad device, carbon-copying a
structural fix from the Linux source project (res/outputs.py there):
Wine's HID backend flags any gamepad-*shaped* device and hardcodes its
Z/Rz axis slots into unipolar XInput trigger semantics, corrupting a
bidirectional rudder signal no matter what AbsInfo range was declared --
fixed there by giving the rudder its own minimal, non-gamepad-shaped
uinput device. That specific mechanism is Wine-only and this Windows
port runs natively (no Wine in the path), so it may not reproduce here
-- but vJoy supports up to 16 devices, the split is cheap, and it's a
proven-working pattern, so it's carried forward defensively rather than
risk the same class of bug blind.

vJoy's own API (via the pyvjoy package) exposes a stable, simple call
shape -- set_axis(axis_id, value), set_button(button_id, is_pressed) --
documented independently of any particular controller, so this module's
mapping logic can be written and tested now even without a Windows
machine to run the real driver against. See
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md for what still
needs verifying: whether pyvjoy + the vJoy driver actually behave this
way on the target Windows version.

build_vjoy_device() is the only piece that touches the real pyvjoy
package, via a lazy import, so this module stays importable (and
GamepadOutput/RudderOutput testable) on a machine with no pyvjoy
installed at all. It is deliberately not covered by this project's unit
tests -- there is nothing to verify without a real vJoy driver running.
"""

from res.logical_input import EAST, NORTH, SOUTH, TL, TR, WEST
from res.rudder import RUDDER_CENTRE

# pyvjoy's set_axis(AxisID, AxisValue) requires AxisID to be one of its
# own HID-usage constants (pyvjoy.HID_USAGE_X etc, from
# pyvjoy/constants.py), not an arbitrary label -- passing anything else
# makes the underlying vJoy SDK call fail with vJoyException. Hardcoded
# here (rather than imported from pyvjoy) so this module stays
# importable without pyvjoy installed; these are fixed vJoy SDK values,
# not pyvjoy-specific behaviour.
VJOY_AXIS_X = 0x30  # pyvjoy.HID_USAGE_X
VJOY_AXIS_Y = 0x31  # pyvjoy.HID_USAGE_Y
VJOY_AXIS_RUDDER = 0x30  # the rudder device's only axis -- its own HID_USAGE_X

GAMEPAD_VJOY_DEVICE_ID = 1
RUDDER_VJOY_DEVICE_ID = 2

# Gamepad device (#1)'s button shape, decided now that a profile
# (res.profiles.PROFILE_DS4) has a verified button_map to build it
# from: one fixed vJoy button number per logical role, shared across
# every profile, so IL-2's bindings stay the same regardless of which
# physical pad drives them. Configure vJoyConf's device #1 with axes
# X, Y and at least 6 buttons; device #2 with a single axis and no
# buttons, to match.
VJOY_BUTTON_MAP = {
    SOUTH: 1,
    EAST: 2,
    WEST: 3,
    NORTH: 4,
    TL: 5,
    TR: 6,
}


class GamepadOutput:
    """Wraps vJoy device #1 (X/Y passthrough + buttons). No rudder axis --
    see RudderOutput -- mirroring the Linux source's build_gamepad_uinput,
    which also carries no rudder axis for the same reason.

    button_index_map: logical button role (res.logical_input values, or
    a test's own strings) -> vJoy button number. A role with no entry is
    a silent no-op, matching an unpopulated/unverified profile's
    button_map (res.profiles.ControllerProfile.button_mapping_verified).
    """

    def __init__(self, device, button_index_map):
        self._device = device
        self._button_index_map = button_index_map

    def set_x(self, value):
        self._device.set_axis(VJOY_AXIS_X, value)

    def set_y(self, value):
        self._device.set_axis(VJOY_AXIS_Y, value)

    def set_button(self, role, pressed):
        button_id = self._button_index_map.get(role)
        if button_id is None:
            return
        self._device.set_button(button_id, pressed)


class RudderOutput:
    """Wraps vJoy device #2: a single axis carrying just the folded rudder
    value, kept off the gamepad device on purpose (see module docstring).
    Mirrors the Linux source's build_rudder_uinput split."""

    def __init__(self, device):
        self._device = device

    def set_rudder(self, value):
        self._device.set_axis(VJOY_AXIS_RUDDER, value)

    def centre_rudder(self):
        self.set_rudder(RUDDER_CENTRE)


def build_vjoy_device(device_id=1):
    """Construct a real pyvjoy.VJoyDevice. Imports pyvjoy lazily so this
    module stays importable without it. Not covered by this project's
    unit tests -- needs a Windows machine with the vJoy driver installed
    to verify at all."""
    import pyvjoy

    return pyvjoy.VJoyDevice(device_id)
