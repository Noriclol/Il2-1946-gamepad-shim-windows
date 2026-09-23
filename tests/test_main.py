import unittest

from res.combo_detector import ComboDetector, Fire, GAMEPAD, KEYBOARD
from res.combos import NORTH, TABLE_1, TABLE_2, TABLE_3, TL, TR, UP, WEST
from res.logical_input import SOUTH
from res.main import EdgeTracker, axis_to_vjoy, run
from res.mouse_look import MouseLookState
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
        mouse_state = MouseLookState()

        run(joystick, PROFILE_DS4, output, rudder_output, mouse_state)

        self.assertEqual(output.x, 16383)
        self.assertEqual(output.y, 16383)
        self.assertEqual(rudder_output.rudder, RUDDER_CENTRE)
        self.assertFalse(any(output.buttons.values()))
        self.assertEqual(mouse_state.get(), (0.0, 0.0))

    def test_pressed_button_forwards_true(self):
        axes = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: -1.0, 5: -1.0}
        buttons = {index: False for index in PROFILE_DS4.button_map.values()}
        buttons[PROFILE_DS4.button_map[SOUTH]] = True
        joystick = _FakeJoystick(axes, buttons)
        output = _FakeOutput()
        rudder_output = _FakeRudderOutput()
        mouse_state = MouseLookState()

        run(joystick, PROFILE_DS4, output, rudder_output, mouse_state)

        self.assertTrue(output.buttons[SOUTH])

    def test_full_right_trigger_pushes_rudder_to_max(self):
        axes = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: -1.0, 5: 1.0}
        buttons = {index: False for index in PROFILE_DS4.button_map.values()}
        joystick = _FakeJoystick(axes, buttons)
        output = _FakeOutput()
        rudder_output = _FakeRudderOutput()
        mouse_state = MouseLookState()

        run(joystick, PROFILE_DS4, output, rudder_output, mouse_state)

        self.assertEqual(rudder_output.rudder, 32767)

    def test_right_stick_deflection_sets_mouse_velocity(self):
        # PROFILE_DS4.axis_map: RX=2, RY=3. Full-right, full-down deflection.
        axes = {0: 0.0, 1: 0.0, 2: 1.0, 3: 1.0, 4: -1.0, 5: -1.0}
        buttons = {index: False for index in PROFILE_DS4.button_map.values()}
        joystick = _FakeJoystick(axes, buttons)
        output = _FakeOutput()
        rudder_output = _FakeRudderOutput()
        mouse_state = MouseLookState()

        run(joystick, PROFILE_DS4, output, rudder_output, mouse_state)

        vx, vy = mouse_state.get()
        self.assertGreater(vx, 0.0)
        self.assertGreater(vy, 0.0)


def _all_buttons_up():
    indices = set(PROFILE_DS4.button_map.values()) | set(
        PROFILE_DS4.dpad_button_map.values()
    )
    return {index: False for index in indices}


class TestComboIntegration(unittest.TestCase):
    def setUp(self):
        self.axes = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: -1.0, 5: -1.0}
        self.buttons = _all_buttons_up()
        self.output = _FakeOutput()
        self.rudder_output = _FakeRudderOutput()
        self.mouse_state = MouseLookState()
        self.combo_detector = ComboDetector()
        self.edge_tracker = EdgeTracker()
        self.fires = []

    def _run(self):
        joystick = _FakeJoystick(self.axes, self.buttons)
        run(
            joystick,
            PROFILE_DS4,
            self.output,
            self.rudder_output,
            self.mouse_state,
            combo_detector=self.combo_detector,
            edge_tracker=self.edge_tracker,
            dispatch_fire=lambda fire, output: self.fires.append(fire),
        )

    def test_table_1_button_then_dpad_direction_fires(self):
        self.buttons[PROFILE_DS4.button_map[NORTH]] = True
        self._run()
        self.assertEqual(self.fires, [])

        self.buttons[PROFILE_DS4.dpad_button_map[UP]] = True
        self._run()
        self.assertEqual(self.fires, [Fire(KEYBOARD, TABLE_1[(NORTH, UP)])])

    def test_table_2_dpad_direction_then_button_fires(self):
        self.buttons[PROFILE_DS4.dpad_button_map[UP]] = True
        self._run()
        self.assertEqual(self.fires, [])

        self.buttons[PROFILE_DS4.button_map[NORTH]] = True
        self._run()
        self.assertEqual(self.fires, [Fire(KEYBOARD, TABLE_2[(UP, NORTH)])])

    def test_held_combo_does_not_refire_every_frame(self):
        self.buttons[PROFILE_DS4.button_map[NORTH]] = True
        self._run()
        self.buttons[PROFILE_DS4.dpad_button_map[UP]] = True
        self._run()
        self.assertEqual(len(self.fires), 1)

        # Nothing changed -- polling the same held state again must not
        # refire the combo.
        self._run()
        self._run()
        self.assertEqual(len(self.fires), 1)

    def test_table_3_both_shoulders_while_face_button_held_fires_self_mapped(self):
        self.buttons[PROFILE_DS4.button_map[WEST]] = True
        self._run()

        self.buttons[PROFILE_DS4.button_map[TL]] = True
        self._run()
        self.assertEqual(self.fires, [])
        # Suppressed: no face-button-less TL passthrough while WEST is held.
        self.assertNotIn(TL, self.output.buttons)

        self.buttons[PROFILE_DS4.button_map[TR]] = True
        self._run()
        self.assertEqual(self.fires, [Fire(GAMEPAD, TABLE_3[WEST])])

    def test_shoulder_forwards_normally_with_no_face_button_held(self):
        self.buttons[PROFILE_DS4.button_map[TL]] = True
        self._run()
        self.assertEqual(self.fires, [])
        self.assertTrue(self.output.buttons[TL])


if __name__ == "__main__":
    unittest.main()
