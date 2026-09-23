import unittest

from res.rudder import RUDDER_CENTRE
from res.vjoy_output import (
    GENERIC_BUTTON_OFFSET,
    VJOY_AXIS_RUDDER,
    VJOY_AXIS_X,
    VJOY_AXIS_Y,
    GamepadOutput,
    RudderOutput,
)


class _FakeVJoyDevice:
    """Records calls instead of talking to a real vJoy driver."""

    def __init__(self):
        self.axis_calls = []
        self.button_calls = []

    def set_axis(self, axis_id, value):
        self.axis_calls.append((axis_id, value))

    def set_button(self, button_id, is_pressed):
        self.button_calls.append((button_id, is_pressed))


class TestGamepadOutputAxes(unittest.TestCase):
    def setUp(self):
        self.device = _FakeVJoyDevice()
        self.output = GamepadOutput(self.device, button_index_map={})

    def test_set_x_writes_x_axis(self):
        self.output.set_x(12345)
        self.assertEqual(self.device.axis_calls, [(VJOY_AXIS_X, 12345)])

    def test_set_y_writes_y_axis(self):
        self.output.set_y(6789)
        self.assertEqual(self.device.axis_calls, [(VJOY_AXIS_Y, 6789)])


class TestRudderOutput(unittest.TestCase):
    """RudderOutput wraps a separate vJoy device (#2), kept off the
    gamepad device -- see res.vjoy_output module docstring for why."""

    def setUp(self):
        self.device = _FakeVJoyDevice()
        self.output = RudderOutput(self.device)

    def test_set_rudder_writes_rudder_axis(self):
        self.output.set_rudder(RUDDER_CENTRE)
        self.assertEqual(self.device.axis_calls, [(VJOY_AXIS_RUDDER, RUDDER_CENTRE)])

    def test_centre_rudder_writes_rudder_centre_value(self):
        self.output.centre_rudder()
        self.assertEqual(self.device.axis_calls, [(VJOY_AXIS_RUDDER, RUDDER_CENTRE)])


class TestGamepadOutputButtons(unittest.TestCase):
    def test_mapped_role_calls_set_button(self):
        device = _FakeVJoyDevice()
        output = GamepadOutput(device, button_index_map={"SOUTH": 1})
        output.set_button("SOUTH", True)
        self.assertEqual(device.button_calls, [(1, True)])

    def test_unmapped_role_is_a_no_op(self):
        device = _FakeVJoyDevice()
        output = GamepadOutput(device, button_index_map={"SOUTH": 1})
        output.set_button("NORTH", True)
        self.assertEqual(device.button_calls, [])

    def test_release_forwards_false(self):
        device = _FakeVJoyDevice()
        output = GamepadOutput(device, button_index_map={"SOUTH": 1})
        output.set_button("SOUTH", False)
        self.assertEqual(device.button_calls, [(1, False)])


class TestGamepadOutputRawButtons(unittest.TestCase):
    def test_raw_button_writes_at_pygame_index_plus_offset(self):
        device = _FakeVJoyDevice()
        output = GamepadOutput(device, button_index_map={})
        output.set_raw_button(11, True)
        self.assertEqual(device.button_calls, [(11 + GENERIC_BUTTON_OFFSET, True)])

    def test_raw_button_release_forwards_false(self):
        device = _FakeVJoyDevice()
        output = GamepadOutput(device, button_index_map={})
        output.set_raw_button(11, False)
        self.assertEqual(device.button_calls, [(11 + GENERIC_BUTTON_OFFSET, False)])


if __name__ == "__main__":
    unittest.main()
