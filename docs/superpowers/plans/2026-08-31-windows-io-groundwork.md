# Windows I/O Groundwork Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Project override: no git operations of any kind** (no `git commit`, `git branch`, etc.) — the user has banned git ops for this project. Every task ends after verification, not a commit. All work happens directly in place on `main`.

**Goal:** Build the parts of the Windows I/O layer (profiles, device scanning, boot-time picker, config persistence, vJoy output mapping) that can be written and unit-tested *today*, without a Windows machine, by being honest about which controller data is actually verified and which is not, and by isolating the pieces that genuinely can't be exercised without real hardware (pygame's device backend, the real vJoy driver) behind small, mockable seams.

**Architecture:** Four modules, each with a hard-real-I/O edge kept as thin and isolated as possible: `res/profiles.py` (pure data + validation), `res/device_scan.py` (pygame enumeration behind a lazy import, plus pure picker-selection logic that takes injected input/output), `res/config.py` (plain JSON file I/O, path injected by the caller), `res/vjoy_output.py` (a `GamepadOutput` class that talks to anything shaped like a vJoy device, plus a `build_vjoy_device()` that's the only place `pyvjoy` is imported, and isn't unit tested). This plan does **not** cover `res/sendinput_output.py` or `res/main.py`'s wiring — see Deferred, below.

**Tech Stack:** Python 3.11+, `pytest`. No new runtime dependency is required to run this plan's own tests — `pygame` and `pyvjoy` are referenced only behind lazy imports inside functions this plan's tests never call.

**Spec:** This plan draws from `~/Projects/Il2-1946-gamepad-shim`'s `docs/findings.md` (the verified 8BitDo SDL axis table) and this repo's own `docs/superpowers/plans/2026-08-31-windows-port-roadmap.md` (the Plan 2 sketch this document supersedes/details) and `res/logical_input.py`, `res/rudder.py`, `res/combos.py` (already-merged portable logic core this plan builds on top of).

## Global Constraints

- No git operations in any task — no commit steps, no branch creation. Work stays uncommitted in the working tree on `main` until the user says otherwise.
- Axis mappings are treated as verified/known for both shipped profiles, per explicit direction: the 8BitDo pad's axis order is grounded in the Linux source's `docs/findings.md` (X=0, Y=1, LT=2, RX=3, RY=4, RT=5); the DS4's axis order follows the standard SDL GameController convention for DualShock 4 pads (X=0, Y=1 left stick, RX=2, RY=3 right stick, LT=4, RT=5 triggers) — this is the widely-documented SDL mapping, not hardware this project has tested directly, but it is treated as reliable enough to build on rather than left unpopulated.
- Button index and hat index mappings are NOT assumed verified for either controller and must not be guessed — both profiles ship with `button_mapping_verified=False` and an empty `button_map`/`hat_index=None`. That data genuinely has no standard convention to fall back on (unlike axes) and needs a real device to establish.
- Every module that touches real device/driver I/O (`pygame`, `pyvjoy`) must do so via a lazy import inside the specific function that needs it, not at module top level — so the module remains importable (and its pure logic testable) on a machine without that package installed.
- No test in this plan requires pygame or pyvjoy to be installed. Tests that need to simulate `pygame` inject a fake module via `unittest.mock.patch.dict(sys.modules, ...)`; tests for vJoy output use a plain Python test double, not `pyvjoy`.

---

## File Structure

```
res/
  profiles.py         # NEW — ControllerProfile dataclass, PROFILE_8BITDO, find_profile()
  device_scan.py       # NEW — DetectedController, enumerate_controllers() (lazy pygame import),
                        #       choose_controller() (pure picker logic, injectable I/O), NoProfileError
  config.py             # NEW — load_last_choice()/save_last_choice(), plain JSON, path injected
  vjoy_output.py          # NEW — GamepadOutput (pure mapping logic against a device-shaped object),
                          #       build_vjoy_device() (lazy pyvjoy import, not unit tested)
tests/
  test_profiles.py
  test_device_scan.py
  test_config.py
  test_vjoy_output.py
```

- `res/profiles.py` has no dependency on `res/device_scan.py` or anything else in this plan — it's pure data.
- `res/device_scan.py` depends on `res/profiles.py` (`find_profile`, `PROFILES`).
- `res/config.py` and `res/vjoy_output.py` are both standalone — no dependency on each other or on `device_scan`/`profiles`, except `vjoy_output.py`'s import of `RUDDER_CENTRE` from the already-merged `res/rudder.py`.

## Deferred (not in this plan)

- `res/sendinput_output.py` — the VK-code-vs-scancode decision for keyboard macros (flagged in the merged logic-core plan's final review) is a real design choice that needs testing on Windows to get right, not something to lock in blind.
- `res/main.py` wiring — the actual event-loop integration needs a live device to iterate against; premature before any of this has run on real hardware.
- Populating either profile's `button_map`/`hat_index` — needs a Windows machine and the physical controller in hand; no standard convention to build on the way axis order has one.

---

### Task 1: Controller profile schema

**Files:**
- Create: `res/profiles.py`
- Test: `tests/test_profiles.py`

**Interfaces:**
- Consumes: nothing from this plan.
- Produces: `res.profiles.AXIS_X`, `AXIS_Y`, `AXIS_LT`, `AXIS_RT`, `AXIS_RX`, `AXIS_RY` (str constants); `REQUIRED_AXIS_ROLES` (tuple of the six axis constants); `ControllerProfile` (frozen dataclass: `name_match: str`, `axis_map: dict`, `button_map: dict = {}`, `hat_index: int | None = None`, `button_mapping_verified: bool = False`; raises `ValueError` in `__post_init__` if `axis_map` is missing any `REQUIRED_AXIS_ROLES` key); `PROFILE_8BITDO`, `PROFILE_DS4` (`ControllerProfile` instances); `PROFILES` (tuple containing both); `find_profile(controller_name: str) -> ControllerProfile | None`.

- [ ] **Step 1: Write the failing test**

`tests/test_profiles.py`:
```python
import unittest

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
            name_match="test-pad",
            axis_map={role: i for i, role in enumerate(REQUIRED_AXIS_ROLES)},
        )
        self.assertEqual(profile.name_match, "test-pad")

    def test_missing_axis_role_raises(self):
        incomplete = {AXIS_X: 0, AXIS_Y: 1}
        with self.assertRaises(ValueError):
            ControllerProfile(name_match="test-pad", axis_map=incomplete)

    def test_defaults_are_unverified_and_empty(self):
        profile = ControllerProfile(
            name_match="test-pad",
            axis_map={role: i for i, role in enumerate(REQUIRED_AXIS_ROLES)},
        )
        self.assertEqual(profile.button_map, {})
        self.assertIsNone(profile.hat_index)
        self.assertFalse(profile.button_mapping_verified)


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

    def test_button_mapping_is_not_yet_verified(self):
        self.assertFalse(PROFILE_DS4.button_mapping_verified)
        self.assertEqual(PROFILE_DS4.button_map, {})
        self.assertIsNone(PROFILE_DS4.hat_index)

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
        # DualShock 4 pad.
        found = find_profile("Wireless Controller")
        self.assertIs(found, PROFILE_DS4)

    def test_no_match_returns_none(self):
        self.assertIsNone(find_profile("Logitech Gamepad F310"))

    def test_empty_name_returns_none(self):
        self.assertIsNone(find_profile(""))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_profiles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.profiles'`

- [ ] **Step 3: Write the implementation**

`res/profiles.py`:
```python
"""Controller profiles: map a physical controller's pygame axis/button/hat
indices onto the logical roles res.rudder / res.mouse_look / res.combos
already operate on.

Axis roles come from res.rudder (LT, RT feed fold_rudder) and
res.mouse_look (RX, RY feed stick_to_velocity), plus X/Y passthrough.
Button/hat roles (when populated) use res.logical_input's SOUTH, NORTH,
EAST, WEST, TL, TR, HAT_X, HAT_Y as button_map keys.

Axis mappings are treated as known/verified for both shipped profiles:
the 8BitDo pad's axis order is verified against real hardware in the
Linux source project's docs/findings.md (X=0, Y=1, LT=2, RX=3, RY=4,
RT=5), and pygame uses the same SDL backend that verification was done
against, so it's carried forward here directly. The DS4's axis order
follows the standard SDL GameController convention for DualShock 4 pads
(X=0, Y=1 left stick, RX=2, RY=3 right stick, LT=4, RT=5 triggers) --
this project hasn't tested a DS4 directly, but that convention is
treated as reliable enough to build on.

Button and hat *index* numbers are NOT assumed verified for either
controller -- SDL/pygame numbers buttons and hats independently of axes
with no equivalent standard convention to fall back on, so guessing here
would be a real risk (wrong button bound to wrong macro) rather than a
reasonable default. See
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md for what still
needs testing on real Windows hardware before button_map/hat_index can
be filled in.
"""

from dataclasses import dataclass, field

AXIS_X = "X"
AXIS_Y = "Y"
AXIS_LT = "LT"
AXIS_RT = "RT"
AXIS_RX = "RX"
AXIS_RY = "RY"

REQUIRED_AXIS_ROLES = (AXIS_X, AXIS_Y, AXIS_LT, AXIS_RT, AXIS_RX, AXIS_RY)


@dataclass(frozen=True)
class ControllerProfile:
    """name_match: a lowercase substring matched against pygame's
    Joystick.get_name(), the same approach the Linux source's
    scan_for_pad used (MATCH = "8bitdo").

    axis_map: logical axis role -> pygame axis index. Must cover every
    role in REQUIRED_AXIS_ROLES or construction raises ValueError.

    button_map: logical button role -> pygame button index. Empty until
    verified against real hardware -- see button_mapping_verified.

    hat_index: pygame hat index carrying the D-pad, or None if not yet
    verified.

    button_mapping_verified: False until button_map/hat_index have been
    confirmed against real hardware. A profile with
    button_mapping_verified=False can still drive the rudder fold, mouse
    look, and X/Y passthrough (all axis-only), but combo macros can't
    run yet.
    """

    name_match: str
    axis_map: dict
    button_map: dict = field(default_factory=dict)
    hat_index: int | None = None
    button_mapping_verified: bool = False

    def __post_init__(self):
        missing = [role for role in REQUIRED_AXIS_ROLES if role not in self.axis_map]
        if missing:
            raise ValueError(
                f"{self.name_match!r} profile missing required axis roles: {missing}"
            )


PROFILE_8BITDO = ControllerProfile(
    name_match="8bitdo",
    axis_map={
        AXIS_X: 0,
        AXIS_Y: 1,
        AXIS_LT: 2,
        AXIS_RX: 3,
        AXIS_RY: 4,
        AXIS_RT: 5,
    },
)

PROFILE_DS4 = ControllerProfile(
    name_match="wireless controller",
    axis_map={
        AXIS_X: 0,
        AXIS_Y: 1,
        AXIS_RX: 2,
        AXIS_RY: 3,
        AXIS_LT: 4,
        AXIS_RT: 5,
    },
)

PROFILES = (PROFILE_8BITDO, PROFILE_DS4)


def find_profile(controller_name):
    """Match a pygame Joystick.get_name() string against known profiles by
    case-insensitive substring, the same approach the Linux source's
    scan_for_pad used. Returns the ControllerProfile, or None if no
    profile matches -- callers show a clear "no profile for this
    controller" message, they don't guess (see res.device_scan)."""
    lowered = controller_name.lower()
    for profile in PROFILES:
        if profile.name_match in lowered:
            return profile
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_profiles.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Verify no regressions**

Run: `pytest -q`
Expected: all previously-passing tests still pass, plus this task's 14 new ones.

---

### Task 2: Device scanning and console picker

**Files:**
- Create: `res/device_scan.py`
- Test: `tests/test_device_scan.py`

**Interfaces:**
- Consumes: `res.profiles.{PROFILES, find_profile}` (Task 1).
- Produces: `res.device_scan.DetectedController` (frozen dataclass: `index: int`, `name: str`, `profile`); `enumerate_controllers() -> list[DetectedController]` (lazy `import pygame` inside the function); `NoProfileError` (Exception subclass); `choose_controller(controllers, remembered_name=None, prompt=input, output=print) -> DetectedController` (raises `NoProfileError` if the chosen controller has no profile; raises `IndexError`-compatible lookup failure — via a plain `StopIteration`-avoiding `next(..., default)` pattern, see implementation — if the user types a number with no matching controller, this plan does not need to handle that gracefully, a later main.py wiring task can add a retry loop).

- [ ] **Step 1: Write the failing test**

`tests/test_device_scan.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_device_scan.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.device_scan'`

- [ ] **Step 3: Write the implementation**

`res/device_scan.py`:
```python
"""Enumerate connected controllers via pygame, match them against known
profiles (res.profiles), and run the boot-time console picker.

pygame.joystick wraps SDL2, giving uniform enumeration across
DirectInput- and XInput-backed devices -- chosen over an XInput-only
library because PlayStation pads don't speak XInput at all (see
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md).

enumerate_controllers() is the only function here that touches the real
pygame package, and does so via a lazy import so this module -- and
choose_controller()'s picker logic -- stay testable on a machine with no
pygame installed at all.
"""

from dataclasses import dataclass

from res.profiles import PROFILES, find_profile


@dataclass(frozen=True)
class DetectedController:
    """index: pygame joystick index at enumeration time -- NOT stable
    across reconnects, callers persist the name (see res.config), not
    the index.
    name: pygame Joystick.get_name().
    profile: the matched ControllerProfile from res.profiles, or None if
    unprofiled."""

    index: int
    name: str
    profile: object


class NoProfileError(Exception):
    """Raised when the user selects a controller with no matching
    ControllerProfile -- see res.profiles.find_profile."""


def enumerate_controllers():
    """Return a DetectedController for every currently connected joystick
    pygame can see. Requires pygame.joystick to already be initialised by
    the caller (pygame.init(); pygame.joystick.init()) -- this function
    doesn't own that lifecycle since a longer-lived caller (res/main.py,
    not built by this plan) needs pygame initialised for the whole
    session, not just this one call."""
    import pygame

    controllers = []
    for i in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(i)
        name = joystick.get_name()
        controllers.append(DetectedController(index=i, name=name, profile=find_profile(name)))
    return controllers


def choose_controller(controllers, remembered_name=None, prompt=input, output=print):
    """Pure selection logic for the boot-time console picker, with
    input/output injected for testability.

    controllers: non-empty list of DetectedController (callers handle the
    empty "no controllers found" case before calling this).
    remembered_name: the previously-chosen controller's name, or None.
    Pre-selected as the default (pressing Enter with no input picks it)
    if still present in controllers; otherwise ignored.
    prompt: callable(message) -> str, defaults to the builtin input.
    output: callable(message) -> None, defaults to the builtin print.

    Returns the chosen DetectedController. Raises NoProfileError if the
    chosen controller has no matching profile.
    """
    default_index = None
    for controller in controllers:
        marker = ""
        if remembered_name is not None and controller.name == remembered_name:
            default_index = controller.index
            marker = "  [last used]"
        output(f"  [{controller.index}] {controller.name}{marker}")

    if default_index is not None:
        raw = prompt(f"Press Enter to use [{default_index}], or type a number: ")
    else:
        raw = prompt(f"Select controller [0-{len(controllers) - 1}]: ")

    raw = raw.strip()
    chosen_index = default_index if (raw == "" and default_index is not None) else int(raw)

    chosen = next(c for c in controllers if c.index == chosen_index)
    if chosen.profile is None:
        supported = ", ".join(p.name_match for p in PROFILES) or "none"
        raise NoProfileError(
            f"No button profile for {chosen.name!r}. Supported controllers: {supported}."
        )
    return chosen
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_device_scan.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Verify no regressions**

Run: `pytest -q`
Expected: all previously-passing tests still pass, plus this task's 9 new ones.

---

### Task 3: Config persistence for the remembered controller choice

**Files:**
- Create: `res/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing from this plan.
- Produces: `load_last_choice(path) -> str | None`; `save_last_choice(path, controller_name)`.

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from res.config import load_last_choice, save_last_choice


class TestConfigRoundTrip(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_last_choice(path, "8BitDo Ultimate Wireless / Pro 2 Wired Controller")
            self.assertEqual(
                load_last_choice(path), "8BitDo Ultimate Wireless / Pro 2 Wired Controller"
            )

    def test_load_missing_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "does-not-exist.json"
            self.assertIsNone(load_last_choice(path))

    def test_load_malformed_json_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{not valid json")
            self.assertIsNone(load_last_choice(path))

    def test_save_creates_parent_directories(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "dir" / "config.json"
            save_last_choice(path, "some controller")
            self.assertTrue(path.exists())
            self.assertEqual(load_last_choice(path), "some controller")

    def test_save_overwrites_previous_choice(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_last_choice(path, "first")
            save_last_choice(path, "second")
            self.assertEqual(load_last_choice(path), "second")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.config'`

- [ ] **Step 3: Write the implementation**

`res/config.py`:
```python
"""Persist the boot-time controller picker's remembered choice.

Plain JSON file, not any platform-specific config API -- keeps this
testable without a real Windows profile directory. The caller (a later
res/main.py, not built by this plan) decides the real path (e.g.
%APPDATA%\\IL2Shim\\config.json on Windows); this module only needs a
path handed to it.
"""

import json
from pathlib import Path


def load_last_choice(path):
    """Return the remembered controller name, or None if no config file
    exists yet, or it's unreadable/malformed."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("last_controller_name")


def save_last_choice(path, controller_name):
    """Write the chosen controller's name to path, creating parent
    directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"last_controller_name": controller_name}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Verify no regressions**

Run: `pytest -q`
Expected: all previously-passing tests still pass, plus this task's 5 new ones.

---

### Task 4: vJoy gamepad output mapping

**Files:**
- Create: `res/vjoy_output.py`
- Test: `tests/test_vjoy_output.py`

**Interfaces:**
- Consumes: `res.rudder.RUDDER_CENTRE` (already merged, portable logic core).
- Produces: `VJOY_AXIS_X`, `VJOY_AXIS_Y`, `VJOY_AXIS_RUDDER` (str constants); `GamepadOutput` (class: `__init__(self, device, button_index_map)`; `set_x(value)`, `set_y(value)`, `set_rudder(value)`, `set_button(role, pressed)`, `centre_rudder()`); `build_vjoy_device(device_id=1)` (lazy `import pyvjoy` inside the function; not unit tested — see Task's Step 5).

- [ ] **Step 1: Write the failing test**

`tests/test_vjoy_output.py`:
```python
import unittest

from res.rudder import RUDDER_CENTRE
from res.vjoy_output import VJOY_AXIS_RUDDER, VJOY_AXIS_X, VJOY_AXIS_Y, GamepadOutput


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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vjoy_output.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.vjoy_output'`

- [ ] **Step 3: Write the implementation**

`res/vjoy_output.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vjoy_output.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Verify no regressions, full suite**

Run: `pytest -q`
Expected: all tests pass — this plan's own 35 (14 + 9 + 5 + 7) plus the already-merged logic-core's 56, for 91 total.

---

## Self-Review Notes

- **Spec coverage:** all four pieces the earlier AskUserQuestion promised (profiles schema, device scan + picker, config persistence, vJoy output mapping interface) are covered by one task each.
- **Verification status, per explicit direction to assume axis mappings are verified:** `PROFILE_8BITDO.axis_map` is genuinely verified data (cited to the Linux source's `docs/findings.md`); `PROFILE_DS4.axis_map` follows the standard SDL GameController convention for DualShock 4 pads, not independently tested by this project but treated as reliable per the user's direction. Both profiles' `button_map`/`hat_index` are still left empty/`None` with `button_mapping_verified=False` — that data has no standard convention to build on, so it stays unpopulated rather than guessed. This is checked by `TestProfile8BitDo.test_button_mapping_is_not_yet_verified`, `TestProfileDS4.test_button_mapping_is_not_yet_verified`, and `TestFindProfile.test_no_match_returns_none`.
- **No placeholders:** every file above is complete, runnable code — no `TBD`/`pass  # implement later`. The two "deliberately not implemented" pieces (`build_vjoy_device`'s real pyvjoy call path, and everything in the Deferred section) are explicitly out of scope, not half-written.
- **No git steps:** confirmed — every task ends at "Verify no regressions," not a commit.
- **Type/name consistency:** `GamepadOutput.set_button`'s `role` parameter and `button_index_map`'s keys are untyped strings in this plan (matching how `res.logical_input`'s roles are already plain strings, per the merged logic core) — a later task wiring a real `ControllerProfile.button_map` into `button_index_map` needs no translation layer, the dict shapes already match.
