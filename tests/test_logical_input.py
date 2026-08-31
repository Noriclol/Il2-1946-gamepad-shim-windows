import unittest

from res.logical_input import (
    DIRECTIONS,
    DOWN,
    EAST,
    FACE_BUTTONS,
    HAT_X,
    HAT_Y,
    LEFT,
    NORTH,
    RIGHT,
    SOUTH,
    UP,
    WEST,
    dpad_direction_for,
)


class TestFaceButtons(unittest.TestCase):
    def test_face_buttons_order_and_membership(self):
        self.assertEqual(FACE_BUTTONS, (WEST, NORTH, SOUTH, EAST))

    def test_face_buttons_are_distinct(self):
        self.assertEqual(len(set(FACE_BUTTONS)), 4)


class TestDirections(unittest.TestCase):
    def test_directions_contains_all_four(self):
        self.assertEqual(DIRECTIONS, frozenset({UP, DOWN, LEFT, RIGHT}))

    def test_direction_string_values(self):
        self.assertEqual(UP, "Up")
        self.assertEqual(DOWN, "Down")
        self.assertEqual(LEFT, "Left")
        self.assertEqual(RIGHT, "Right")


class TestDpadDirectionFor(unittest.TestCase):
    def test_zero_is_neutral(self):
        self.assertIsNone(dpad_direction_for(HAT_X, 0))
        self.assertIsNone(dpad_direction_for(HAT_Y, 0))

    def test_hat_x_signs(self):
        self.assertEqual(dpad_direction_for(HAT_X, -1), LEFT)
        self.assertEqual(dpad_direction_for(HAT_X, 1), RIGHT)

    def test_hat_y_signs(self):
        self.assertEqual(dpad_direction_for(HAT_Y, -1), UP)
        self.assertEqual(dpad_direction_for(HAT_Y, 1), DOWN)

    def test_arbitrary_positive_and_negative_magnitude_map_by_sign_only(self):
        # A real HID hat can report values like -32768/32767, not just -1/1 —
        # dpad_direction_for must key off sign only, matching the Linux
        # source's behaviour (see docs/button_combo_mappings.md).
        self.assertEqual(dpad_direction_for(HAT_X, -32768), LEFT)
        self.assertEqual(dpad_direction_for(HAT_X, 32767), RIGHT)


if __name__ == "__main__":
    unittest.main()
