"""Translate the shim's logical outputs (folded rudder axis, passthrough
X/Y, buttons) onto a vJoy virtual device.

vJoy's own API (via the pyvjoy package) exposes a stable, simple call
shape -- set_axis(axis_id, value), set_button(button_id, is_pressed) --
documented independently of any particular controller, so this module's
mapping logic can be written and tested now even without a Windows
machine to run the real driver against. See
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md for what still
needs verifying: whether pyvjoy + the vJoy driver actually behave this
way on the target Windows version, and the exact vJoy device #1 shape
configured via vJoyConf (axis count, button count, POV hat) -- not yet
decided since it depends on button_map/hat_index being populated for at
least one profile first (res/profiles.py).

build_vjoy_device() is the only piece that touches the real pyvjoy
package, via a lazy import, so this module stays importable (and
GamepadOutput testable) on a machine with no pyvjoy installed at all.
It is deliberately not covered by this project's unit tests -- there is
nothing to verify without a real vJoy driver running.
"""

from res.rudder import RUDDER_CENTRE

VJOY_AXIS_X = "X"
VJOY_AXIS_Y = "Y"
VJOY_AXIS_RUDDER = "RZ"


class GamepadOutput:
    """Wraps a vJoy-device-shaped object (anything with set_axis(axis_id,
    value) and set_button(button_id, is_pressed) methods -- pyvjoy's
    VJoyDevice satisfies this, and so does a test double) and translates
    logical roles into calls on it.

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

    def set_rudder(self, value):
        self._device.set_axis(VJOY_AXIS_RUDDER, value)

    def set_button(self, role, pressed):
        button_id = self._button_index_map.get(role)
        if button_id is None:
            return
        self._device.set_button(button_id, pressed)

    def centre_rudder(self):
        self.set_rudder(RUDDER_CENTRE)


def build_vjoy_device(device_id=1):
    """Construct a real pyvjoy.VJoyDevice. Imports pyvjoy lazily so this
    module stays importable without it. Not covered by this project's
    unit tests -- needs a Windows machine with the vJoy driver installed
    to verify at all."""
    import pyvjoy

    return pyvjoy.VJoyDevice(device_id)
