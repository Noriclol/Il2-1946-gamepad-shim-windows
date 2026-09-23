import unittest

from res.logical_input import DOWN, EAST, LEFT, NORTH, RIGHT, SOUTH, TL, TR, UP, WEST
from res.profiles import (
    AXIS_LT,
    AXIS_RT,
    AXIS_RX,
    AXIS_RY,
    AXIS_X,
    AXIS_Y,
    PROFILE_8BITDO,
    PROFILE_DS4,
    PROFILES,
    REQUIRED_AXIS_ROLES,
    ControllerProfile,
    find_profile,
)


class TestControllerProfileValidation(unittest.TestCase):
    def test_complete_axis_map_constructs_fine(self):
        profile = ControllerProfile(
            name_match=("test-pad",),
            axis_map={role: i for i, role in enumerate(REQUIRED_AXIS_ROLES)},
        )
        self.assertEqual(profile.name_match, ("test-pad",))

    def test_missing_axis_role_raises(self):
        incomplete = {AXIS_X: 0, AXIS_Y: 1}
        with self.assertRaises(ValueError):
            ControllerProfile(name_match=("test-pad",), axis_map=incomplete)

    def test_defaults_are_unverified_and_empty(self):
        profile = ControllerProfile(
            name_match=("test-pad",),
            axis_map={role: i for i, role in enumerate(REQUIRED_AXIS_ROLES)},
        )
        self.assertEqual(profile.button_map, {})
        self.assertIsNone(profile.hat_index)
        self.assertFalse(profile.button_mapping_verified)
        self.assertEqual(profile.dpad_button_map, {})
        self.assertFalse(profile.dpad_mapping_verified)


class TestProfile8BitDo(unittest.TestCase):
    def test_axis_map_matches_verified_findings(self):
        # Verified against real hardware in the Linux source project's
        # docs/findings.md SDL axis table.
        self.assertEqual(
            PROFILE_8BITDO.axis_map,
            {AXIS_X: 0, AXIS_Y: 1, AXIS_LT: 2, AXIS_RX: 3, AXIS_RY: 4, AXIS_RT: 5},
        )

    def test_button_mapping_is_not_yet_verified(self):
        self.assertFalse(PROFILE_8BITDO.button_mapping_verified)
        self.assertEqual(PROFILE_8BITDO.button_map, {})
        self.assertIsNone(PROFILE_8BITDO.hat_index)

    def test_is_registered(self):
        self.assertIn(PROFILE_8BITDO, PROFILES)


class TestProfileDS4(unittest.TestCase):
    def test_axis_map_matches_standard_sdl_layout(self):
        # Standard SDL GameController convention for DualShock 4 pads —
        # not independently verified against this project's own
        # hardware, but treated as reliable enough to build on.
        self.assertEqual(
            PROFILE_DS4.axis_map,
            {AXIS_X: 0, AXIS_Y: 1, AXIS_RX: 2, AXIS_RY: 3, AXIS_LT: 4, AXIS_RT: 5},
        )

    def test_button_mapping_is_verified_from_real_hardware(self):
        # Verified against a real DS4 via scripts/windows_diagnostics.py
        # on Windows, 2026-09-23.
        self.assertTrue(PROFILE_DS4.button_mapping_verified)
        self.assertEqual(
            PROFILE_DS4.button_map,
            {SOUTH: 0, EAST: 1, WEST: 2, NORTH: 3, TL: 9, TR: 10},
        )
        # This pad reports 0 hats -- its D-pad is exposed as extra
        # buttons instead, so hat_index stays unverified/unpopulated.
        self.assertIsNone(PROFILE_DS4.hat_index)

    def test_dpad_button_map_is_guessed_and_unverified(self):
        # Only UP=15 is confirmed against real hardware (2026-09-23
        # diagnostic run); DOWN/LEFT/RIGHT are a guessed sequential
        # continuation pending confirmation.
        self.assertEqual(
            PROFILE_DS4.dpad_button_map,
            {UP: 15, DOWN: 16, LEFT: 17, RIGHT: 18},
        )
        self.assertFalse(PROFILE_DS4.dpad_mapping_verified)

    def test_is_registered(self):
        self.assertIn(PROFILE_DS4, PROFILES)


class TestFindProfile(unittest.TestCase):
    def test_matches_8bitdo_case_insensitive_substring(self):
        found = find_profile("8BitDo Ultimate Wireless / Pro 2 Wired Controller")
        self.assertIs(found, PROFILE_8BITDO)

    def test_matches_8bitdo_lowercase_name(self):
        found = find_profile("8bitdo ultimate wireless")
        self.assertIs(found, PROFILE_8BITDO)

    def test_matches_ds4_by_wireless_controller_name(self):
        # "Wireless Controller" is the common pygame/SDL device name for a
        # DualShock 4 pad connected over Bluetooth.
        found = find_profile("Wireless Controller")
        self.assertIs(found, PROFILE_DS4)

    def test_matches_ds4_by_ps4_controller_name(self):
        # "PS4 Controller" is what a real DS4 reported over USB in a
        # Windows diagnostic run (log.txt, 2026-09-23).
        found = find_profile("PS4 Controller")
        self.assertIs(found, PROFILE_DS4)

    def test_no_match_returns_none(self):
        self.assertIsNone(find_profile("Logitech Gamepad F310"))

    def test_empty_name_returns_none(self):
        self.assertIsNone(find_profile(""))


if __name__ == "__main__":
    unittest.main()
