import unittest

from res.logical_input import SOUTH
from res.main import axis_to_vjoy, run
from res.profiles import PROFILE_DS4
from res.rudder import RUDDER_CENTRE


class _FakeJoystick:
    """Records nothing, just serves canned axis/button values by index --
    the same shape pygame's Joystick offers (get_axis, get_button)."""

    def __init__(self, axes, buttons):
        self._axes = axes
        self._buttons = buttons

    def get_axis(self, index):
        return self._axes[index]

    def get_button(self, index):
        return self._buttons[index]


class _FakeOutput:
    """Records calls instead of talking to a real vJoy gamepad device."""

    def __init__(self):
        self.x = None
        self.y = None
        self.buttons = {}

    def set_x(self, value):
        self.x = value

    def set_y(self, value):
        self.y = value

    def set_button(self, role, pressed):
        self.buttons[role] = pressed


class _FakeRudderOutput:
    """Records calls instead of talking to a real, separate vJoy rudder
    device -- see res.vjoy_output for why the rudder is its own device."""

    def __init__(self):
        self.rudder = None

    def set_rudder(self, value):
        self.rudder = value


class TestAxisToVjoy(unittest.TestCase):
    def test_centre_maps_to_midpoint(self):
        self.assertEqual(axis_to_vjoy(0.0), 16383)

    def test_min_maps_to_zero(self):
        self.assertEqual(axis_to_vjoy(-1.0), 0)

    def test_max_maps_to_vjoy_max(self):
        self.assertEqual(axis_to_vjoy(1.0), 32767)


class TestRun(unittest.TestCase):
    def test_neutral_stick_and_triggers_centre_everything(self):
        # PROFILE_DS4.axis_map: X=0, Y=1, RX=2, RY=3, LT=4, RT=5.
        # SDL trigger axes rest at -1.0 (unpressed).
        axes = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: -1.0, 5: -1.0}
        buttons = {index: False for index in PROFILE_DS4.button_map.values()}
        joystick = _FakeJoystick(axes, buttons)
        output = _FakeOutput()
        rudder_output = _FakeRudderOutput()

        run(joystick, PROFILE_DS4, output, rudder_output)

        self.assertEqual(output.x, 16383)
        self.assertEqual(output.y, 16383)
        self.assertEqual(rudder_output.rudder, RUDDER_CENTRE)
        self.assertFalse(any(output.buttons.values()))

    def test_pressed_button_forwards_true(self):
        axes = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: -1.0, 5: -1.0}
        buttons = {index: False for index in PROFILE_DS4.button_map.values()}
        buttons[PROFILE_DS4.button_map[SOUTH]] = True
        joystick = _FakeJoystick(axes, buttons)
        output = _FakeOutput()
        rudder_output = _FakeRudderOutput()

        run(joystick, PROFILE_DS4, output, rudder_output)

        self.assertTrue(output.buttons[SOUTH])

    def test_full_right_trigger_pushes_rudder_to_max(self):
        axes = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: -1.0, 5: 1.0}
        buttons = {index: False for index in PROFILE_DS4.button_map.values()}
        joystick = _FakeJoystick(axes, buttons)
        output = _FakeOutput()
        rudder_output = _FakeRudderOutput()

        run(joystick, PROFILE_DS4, output, rudder_output)

        self.assertEqual(rudder_output.rudder, 32767)


if __name__ == "__main__":
    unittest.main()
