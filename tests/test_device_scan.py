import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from res.device_scan import DetectedController, NoProfileError, choose_controller, enumerate_controllers
from res.profiles import PROFILE_8BITDO, PROFILE_DS4


def _fake_prompt(answers):
    """Returns a callable usable as choose_controller's prompt=, yielding
    each of answers in order on successive calls."""
    it = iter(answers)

    def prompt(_message):
        return next(it)

    return prompt


class TestChooseController(unittest.TestCase):
    def setUp(self):
        self.controllers = [
            DetectedController(index=0, name="8BitDo Ultimate Wireless / Pro 2 Wired Controller", profile=PROFILE_8BITDO),
            DetectedController(index=1, name="Logitech Gamepad F310", profile=None),
        ]

    def test_explicit_number_selection(self):
        chosen = choose_controller(
            self.controllers, prompt=_fake_prompt(["0"]), output=lambda _m: None
        )
        self.assertEqual(chosen.index, 0)

    def test_enter_with_remembered_name_picks_it(self):
        chosen = choose_controller(
            self.controllers,
            remembered_name="8BitDo Ultimate Wireless / Pro 2 Wired Controller",
            prompt=_fake_prompt([""]),
            output=lambda _m: None,
        )
        self.assertEqual(chosen.index, 0)

    def test_remembered_name_marks_the_listing(self):
        printed = []
        choose_controller(
            self.controllers,
            remembered_name="8BitDo Ultimate Wireless / Pro 2 Wired Controller",
            prompt=_fake_prompt([""]),
            output=printed.append,
        )
        self.assertTrue(any("[last used]" in line for line in printed))

    def test_no_remembered_name_prompts_without_default(self):
        prompts_seen = []

        def prompt(message):
            prompts_seen.append(message)
            return "0"

        choose_controller(self.controllers, prompt=prompt, output=lambda _m: None)
        self.assertIn("Select controller", prompts_seen[0])

    def test_unprofiled_choice_raises_no_profile_error(self):
        with self.assertRaises(NoProfileError):
            choose_controller(
                self.controllers, prompt=_fake_prompt(["1"]), output=lambda _m: None
            )

    def test_no_profile_error_names_supported_controllers(self):
        try:
            choose_controller(
                self.controllers, prompt=_fake_prompt(["1"]), output=lambda _m: None
            )
            self.fail("expected NoProfileError")
        except NoProfileError as exc:
            self.assertIn("8bitdo", str(exc))


class TestEnumerateControllers(unittest.TestCase):
    def test_wraps_pygame_joystick_enumeration(self):
        fake_joystick_0 = SimpleNamespace(get_name=lambda: "8BitDo Ultimate Wireless / Pro 2 Wired Controller")
        fake_joystick_1 = SimpleNamespace(get_name=lambda: "Wireless Controller")
        fake_pygame = SimpleNamespace(
            joystick=SimpleNamespace(
                get_count=lambda: 2,
                Joystick=lambda i: (fake_joystick_0, fake_joystick_1)[i],
            )
        )
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            controllers = enumerate_controllers()

        self.assertEqual(len(controllers), 2)
        self.assertEqual(controllers[0].name, "8BitDo Ultimate Wireless / Pro 2 Wired Controller")
        self.assertIs(controllers[0].profile, PROFILE_8BITDO)
        self.assertEqual(controllers[1].name, "Wireless Controller")
        self.assertIs(controllers[1].profile, PROFILE_DS4)

    def test_unprofiled_device_gets_none(self):
        fake_joystick = SimpleNamespace(get_name=lambda: "Logitech Gamepad F310")
        fake_pygame = SimpleNamespace(
            joystick=SimpleNamespace(get_count=lambda: 1, Joystick=lambda i: fake_joystick)
        )
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            controllers = enumerate_controllers()

        self.assertEqual(len(controllers), 1)
        self.assertIsNone(controllers[0].profile)

    def test_no_devices_returns_empty_list(self):
        fake_pygame = SimpleNamespace(
            joystick=SimpleNamespace(get_count=lambda: 0, Joystick=lambda i: None)
        )
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            controllers = enumerate_controllers()

        self.assertEqual(controllers, [])


if __name__ == "__main__":
    unittest.main()
