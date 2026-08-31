import unittest

from res.combo_detector import ComboDetector, Fire, GAMEPAD, KEYBOARD
from res.combos import EAST, NORTH, SOUTH, TABLE_1, TABLE_2, TABLE_3, TL, TR, WEST


class TestTable1Firing(unittest.TestCase):
    def setUp(self):
        self.detector = ComboDetector()

    def test_button_then_direction_fires(self):
        self.assertEqual(self.detector.on_face_button(NORTH, True), [])
        fires = self.detector.on_dpad_direction("Up", True)
        self.assertEqual(fires, [Fire(KEYBOARD, TABLE_1[(NORTH, "Up")])])

    def test_lone_button_tap_fires_nothing(self):
        self.assertEqual(self.detector.on_face_button(NORTH, True), [])
        self.assertEqual(self.detector.on_face_button(NORTH, False), [])

    def test_lone_direction_tap_fires_nothing(self):
        self.assertEqual(self.detector.on_dpad_direction("Up", True), [])
        self.assertEqual(self.detector.on_dpad_direction("Up", False), [])

    def test_repeated_taps_refire_while_held(self):
        self.detector.on_face_button(NORTH, True)
        first = self.detector.on_dpad_direction("Up", True)
        self.detector.on_dpad_direction("Up", False)
        second = self.detector.on_dpad_direction("Up", True)
        self.assertEqual(first, second)
        self.assertEqual(first, [Fire(KEYBOARD, TABLE_1[(NORTH, "Up")])])

    def test_starter_release_disarms(self):
        self.detector.on_face_button(NORTH, True)
        self.detector.on_face_button(NORTH, False)
        fires = self.detector.on_dpad_direction("Up", True)
        self.assertEqual(fires, [])


class TestTable2Firing(unittest.TestCase):
    def setUp(self):
        self.detector = ComboDetector()

    def test_direction_then_button_fires(self):
        self.assertEqual(self.detector.on_dpad_direction("Up", True), [])
        fires = self.detector.on_face_button(NORTH, True)
        self.assertEqual(fires, [Fire(KEYBOARD, TABLE_2[("Up", NORTH)])])


class TestRoleLock(unittest.TestCase):
    def setUp(self):
        self.detector = ComboDetector()

    def test_completer_does_not_retroactively_become_starter(self):
        self.detector.on_face_button(NORTH, True)
        first = self.detector.on_dpad_direction("Up", True)
        self.assertEqual(first, [Fire(KEYBOARD, TABLE_1[(NORTH, "Up")])])

        second = self.detector.on_face_button(SOUTH, True)
        self.assertEqual(second, [])


class TestTable3Firing(unittest.TestCase):
    def setUp(self):
        self.detector = ComboDetector()

    def test_shoulders_forward_when_no_face_button_held(self):
        fires, forward = self.detector.on_shoulder(TL, True)
        self.assertEqual(fires, [])
        self.assertTrue(forward)

    def test_both_shoulders_while_button_held_fires_self_mapped(self):
        self.detector.on_face_button(WEST, True)

        fires, forward = self.detector.on_shoulder(TL, True)
        self.assertEqual(fires, [])
        self.assertFalse(forward)

        fires, forward = self.detector.on_shoulder(TR, True)
        self.assertEqual(fires, [Fire(GAMEPAD, TABLE_3[WEST])])
        self.assertFalse(forward)

    def test_releasing_and_repressing_a_shoulder_refires(self):
        self.detector.on_face_button(EAST, True)
        self.detector.on_shoulder(TL, True)
        self.detector.on_shoulder(TR, True)
        self.detector.on_shoulder(TL, False)

        fires, forward = self.detector.on_shoulder(TL, True)
        self.assertEqual(fires, [Fire(GAMEPAD, TABLE_3[EAST])])
        self.assertFalse(forward)


if __name__ == "__main__":
    unittest.main()
