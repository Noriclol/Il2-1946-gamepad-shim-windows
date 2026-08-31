import unittest

from res.combos import (
    DIRECTIONS,
    EAST,
    FACE_BUTTONS,
    HAT_X,
    HAT_Y,
    NORTH,
    SOUTH,
    TABLE_1,
    TABLE_2,
    TABLE_3,
    WEST,
    dpad_direction_for,
)


class TestTableShape(unittest.TestCase):
    def test_table_1_has_16_entries(self):
        self.assertEqual(len(TABLE_1), 16)

    def test_table_2_has_16_entries(self):
        self.assertEqual(len(TABLE_2), 16)

    def test_table_3_has_4_entries(self):
        self.assertEqual(len(TABLE_3), 4)

    def test_table_1_covers_every_button_direction_pair(self):
        expected = {(b, d) for b in FACE_BUTTONS for d in DIRECTIONS}
        self.assertEqual(set(TABLE_1.keys()), expected)

    def test_table_2_covers_every_direction_button_pair(self):
        expected = {(d, b) for d in DIRECTIONS for b in FACE_BUTTONS}
        self.assertEqual(set(TABLE_2.keys()), expected)

    def test_table_3_is_self_mapped_for_every_face_button(self):
        self.assertEqual(set(TABLE_3.keys()), set(FACE_BUTTONS))
        for button, output in TABLE_3.items():
            self.assertEqual(button, output)

    def test_keyboard_outputs_are_all_distinct(self):
        outputs = list(TABLE_1.values()) + list(TABLE_2.values())
        self.assertEqual(len(outputs), len(set(outputs)))

    def test_keyboard_outputs_are_plain_glyph_strings(self):
        # No evdev dependency in this project — outputs are glyphs the
        # Windows output layer (a later plan) will translate to a
        # SendInput keystroke, not evdev KEY_* integers.
        outputs = list(TABLE_1.values()) + list(TABLE_2.values())
        self.assertTrue(all(isinstance(o, str) for o in outputs))

    def test_specific_ported_mappings(self):
        # Spot-check a few known assignments, carried over from the Linux
        # source's docs/button_combo_mappings.md.
        self.assertEqual(TABLE_1[(WEST, "Up")], "Q")
        self.assertEqual(TABLE_1[(NORTH, "Down")], "F")
        self.assertEqual(TABLE_2[("Up", SOUTH)], "Ö")
        self.assertEqual(TABLE_2[("Right", WEST)], "Å")
        self.assertEqual(TABLE_3[EAST], EAST)


class TestDpadDirectionFor(unittest.TestCase):
    def test_zero_is_neutral(self):
        self.assertIsNone(dpad_direction_for(HAT_X, 0))
        self.assertIsNone(dpad_direction_for(HAT_Y, 0))

    def test_hat_x_signs(self):
        self.assertEqual(dpad_direction_for(HAT_X, -1), "Left")
        self.assertEqual(dpad_direction_for(HAT_X, 1), "Right")

    def test_hat_y_signs(self):
        self.assertEqual(dpad_direction_for(HAT_Y, -1), "Up")
        self.assertEqual(dpad_direction_for(HAT_Y, 1), "Down")


if __name__ == "__main__":
    unittest.main()
