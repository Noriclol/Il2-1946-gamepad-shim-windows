# Portable Logic Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the OS-independent math and logic from the Linux `Il2-1946-gamepad-shim` project (rudder-fold, right-stick-to-mouse-velocity math, chorded-button-combo tables and detection) into this Windows repo, with zero dependency on `evdev` or any other Linux-only package — fully unit-testable today, with no Windows machine required.

**Architecture:** Four small modules with no OS calls at all (`logical_input.py`, `rudder.py`, `mouse_look.py`, `combos.py`) plus a pure state-machine (`combo_detector.py`). All inputs/outputs are plain Python values (floats, ints, strings) — no `evdev`, no `pygame`, no Win32 calls. The later Windows I/O layer (a separate plan) adapts pygame device events and vJoy/SendInput output onto this core; this plan does not touch that layer.

**Tech Stack:** Python 3.11+, `pytest` for tests, no other runtime dependencies for this plan.

**Spec:** This plan draws its behavior from the source Linux project at `~/Projects/Il2-1946-gamepad-shim` — specifically `res/rudder.py`, `res/mouse_look.py`, `res/combos.py`, `res/combo_detector.py` and their tests, plus `docs/architecture.md` (§Rudder fold, §Right-stick-to-mouse translation, §Chord macros) and `docs/button_combo_mappings.md`. There is no separate written spec doc in this repo — the plan itself documents the porting decisions inline.

## Global Constraints

- No `evdev` (or any Linux-only package) import anywhere in this plan's code — it must run and test green on both Linux and Windows dev machines.
- Preserve numeric behavior exactly where the Linux source has verified-correct math (rudder fold, deadzone/expo curves, `RelAccumulator`) — port the math verbatim, only replace the identifiers that were evdev-specific.
- Keyboard-macro outputs (`TABLE_1`/`TABLE_2` values) become plain glyph strings (`"Q"`, `"Ö"`, `"."`, etc.) instead of `evdev.ecodes.KEY_*` constants — the Windows output layer (a later plan) is responsible for turning a glyph into a `SendInput` keystroke; this layer only needs to name *which* glyph.
- Gamepad-macro outputs (`TABLE_3` values) stay self-mapped logical button roles (`WEST -> WEST`, etc.), same as the Linux source.
- Every module and test file in this plan must have no import of `res.combo_detector`/`res.combos` reaching into a later plan's not-yet-written code — check imports resolve within this plan's own file set.

---

## File Structure

```
res/
  __init__.py              # empty, package marker
  logical_input.py         # NEW — abstract button/direction roles, no evdev
  rudder.py                 # ported verbatim from Linux source (already OS-independent)
  mouse_look.py             # ported, trimmed: drops mouse_tick_loop (evdev-specific; belongs to a later plan)
  combos.py                  # rewritten: same table shape, glyph-string outputs instead of evdev KEY_* codes
  combo_detector.py          # ported verbatim logic, updated imports only
tests/
  __init__.py
  test_rudder.py             # ported verbatim
  test_mouse_look.py          # ported verbatim (existing tests never touched mouse_tick_loop)
  test_combos.py               # ported, one test adjusted to check glyph strings instead of evdev KEY_* codes
  test_combo_detector.py        # ported verbatim
pytest.ini
requirements-dev.txt
```

- `logical_input.py` exists so `combos.py` and `combo_detector.py` have a vocabulary of button/direction identifiers that isn't `evdev.ecodes` — on Linux those were Linux kernel input-event-code integers; here they're plain strings, since nothing in this plan's logic cares about the underlying integer value, only about equality/hashing for dict keys.
- `rudder.py` needs no changes at all — it already takes plain numbers in, plain numbers out.
- `mouse_look.py` keeps every function/class already covered by `test_mouse_look.py` and drops only `mouse_tick_loop`, which does `from evdev import ecodes as e` and calls `ui_mouse.write(...)` — that's Windows-output plumbing (SendInput-based, in a later plan), not portable math.

---

### Task 1: Project scaffolding + logical input roles

**Files:**
- Create: `res/__init__.py`
- Create: `tests/__init__.py`
- Create: `pytest.ini`
- Create: `requirements-dev.txt`
- Create: `res/logical_input.py`
- Test: `tests/test_logical_input.py`

**Interfaces:**
- Produces: `res.logical_input.SOUTH`, `NORTH`, `EAST`, `WEST`, `TL`, `TR` (str constants); `FACE_BUTTONS` (tuple of the four face-button constants, order `(WEST, NORTH, SOUTH, EAST)` — matches the Linux source's `FACE_BUTTONS` ordering exactly, since `combos.py`'s Table 1/2 completeness checks iterate it); `HAT_X`, `HAT_Y` (str constants); `UP`, `DOWN`, `LEFT`, `RIGHT` (str constants, values `"Up"`, `"Down"`, `"Left"`, `"Right"` — same string values as the Linux source uses, since later tests compare against literal `"Up"` etc.); `DIRECTIONS` (frozenset of the four direction constants); `dpad_direction_for(axis, value)` (function, `axis` is `HAT_X` or `HAT_Y`, `value` is a signed int, returns a direction constant or `None`).

- [ ] **Step 1: Create empty package markers**

```bash
mkdir -p res tests
touch res/__init__.py
touch tests/__init__.py
```

- [ ] **Step 2: Create pytest config**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 3: Create dev requirements**

`requirements-dev.txt`:
```
pytest>=8.0
```

- [ ] **Step 4: Write the failing test for logical_input**

`tests/test_logical_input.py`:
```python
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
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `pytest tests/test_logical_input.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.logical_input'`

- [ ] **Step 6: Write the implementation**

`res/logical_input.py`:
```python
"""Abstract input roles, independent of any OS input API or physical
controller layout.

The Linux project used evdev's kernel input-event-code integers
(BTN_WEST, ABS_HAT0X, ...) as the vocabulary res/combos.py and
res/combo_detector.py operate on. evdev doesn't exist on Windows (it
wraps Linux-only kernel headers), so this module replaces that
vocabulary with plain strings — nothing downstream cares about the
underlying value, only about equality/hashing for dict keys.
"""

SOUTH = "SOUTH"
NORTH = "NORTH"
EAST = "EAST"
WEST = "WEST"
TL = "TL"
TR = "TR"

FACE_BUTTONS = (WEST, NORTH, SOUTH, EAST)

HAT_X = "HAT_X"
HAT_Y = "HAT_Y"

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"
DIRECTIONS = frozenset({UP, DOWN, LEFT, RIGHT})

# Signs match the Linux project's old input-remapper-preset convention
# ("DPad-Y Down" used +30, "DPad-Y Up" used -30) — see the source repo's
# docs/findings.md.
_DIRECTION_BY_AXIS_SIGN = {
    (HAT_X, -1): LEFT,
    (HAT_X, 1): RIGHT,
    (HAT_Y, -1): UP,
    (HAT_Y, 1): DOWN,
}


def dpad_direction_for(axis, value):
    """Map a signed hat-axis value to a direction constant, or None for
    neutral (value == 0). Keys off sign only, so it works whether the
    caller passes -1/1 or a full-range HID value like -32768/32767."""
    if value == 0:
        return None
    sign = 1 if value > 0 else -1
    return _DIRECTION_BY_AXIS_SIGN.get((axis, sign))
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `pytest tests/test_logical_input.py -v`
Expected: PASS (7 tests)

- [ ] **Step 8: Commit**

```bash
git add res/__init__.py tests/__init__.py pytest.ini requirements-dev.txt res/logical_input.py tests/test_logical_input.py
git commit -m "feat: add logical input roles module, replacing evdev vocabulary"
```

---

### Task 2: Rudder fold

**Files:**
- Create: `res/rudder.py`
- Test: `tests/test_rudder.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `res.rudder.DEFAULT_DEADZONE` (float, `0.05`), `DEFAULT_EXPO` (float, `1.0`), `RUDDER_MIN` (int, `0`), `RUDDER_MAX` (int, `32767`), `RUDDER_CENTRE` (int, `16383`); `normalize(value, info_min, info_max)` (float); `fold_rudder(lt_value, lt_min, lt_max, rt_value, rt_min, rt_max, deadzone=DEFAULT_DEADZONE, expo=DEFAULT_EXPO, invert=False)` (int in `RUDDER_MIN..RUDDER_MAX`).

- [ ] **Step 1: Write the failing test**

`tests/test_rudder.py` (ported verbatim from the Linux source — this math has no OS dependency at all):
```python
import unittest

from res.rudder import RUDDER_CENTRE, RUDDER_MAX, RUDDER_MIN, fold_rudder, normalize


class TestNormalize(unittest.TestCase):
    def test_min_maps_to_zero(self):
        self.assertAlmostEqual(normalize(-32768, -32768, 32767), 0.0)

    def test_max_maps_to_one(self):
        self.assertAlmostEqual(normalize(32767, -32768, 32767), 1.0)

    def test_zero_span_returns_zero(self):
        self.assertEqual(normalize(5, 5, 5), 0.0)


class TestFoldRudder(unittest.TestCase):
    AXIS = dict(lt_min=-32768, lt_max=32767, rt_min=-32768, rt_max=32767)

    def fold(self, lt_value, rt_value, **kwargs):
        return fold_rudder(
            lt_value, self.AXIS["lt_min"], self.AXIS["lt_max"],
            rt_value, self.AXIS["rt_min"], self.AXIS["rt_max"],
            **kwargs,
        )

    def test_both_released_centres(self):
        self.assertEqual(self.fold(-32768, -32768), RUDDER_CENTRE)

    def test_left_full_pulls_to_min(self):
        self.assertEqual(self.fold(32767, -32768), RUDDER_MIN)

    def test_right_full_pulls_to_max(self):
        self.assertEqual(self.fold(-32768, 32767), RUDDER_MAX)

    def test_both_full_centres(self):
        self.assertEqual(self.fold(32767, 32767), RUDDER_CENTRE)

    def test_deadzone_suppresses_small_values(self):
        rt_value = -32768 + int(0.02 * 65535)
        self.assertEqual(self.fold(-32768, rt_value), RUDDER_CENTRE)

    def test_invert_mirrors_around_centre(self):
        normal = self.fold(32767, -32768)
        inverted = self.fold(32767, -32768, invert=True)
        self.assertEqual(inverted, RUDDER_MAX - normal)

    def test_output_never_negative(self):
        for lt in (-32768, 0, 32767):
            for rt in (-32768, 0, 32767):
                self.assertGreaterEqual(self.fold(lt, rt), RUDDER_MIN)
                self.assertLessEqual(self.fold(lt, rt), RUDDER_MAX)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rudder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.rudder'`

- [ ] **Step 3: Write the implementation**

`res/rudder.py` (verbatim from the Linux source — no evdev import existed here to begin with):
```python
"""Fold two independent trigger axes into one rudder axis.

  LT released -> centre, pulled -> rudder toward RUDDER_MIN
  RT released -> centre, pulled -> rudder toward RUDDER_MAX
  both pulled or both released -> centred

Output is published as a UNIPOLAR 0..32767 range with centre at the
midpoint, not a bipolar -32768..32767 range. The Linux source project
found (empirically, via IL-2 1946's own rudder calibration screen) that
the game clamps negative axis values to 0 and only displays/uses the
positive half of a bipolar signal — so the whole range needs to live in
"positive" axis space for the game to read it as a full-travel control.
Carrying this convention forward for the Windows port since it's a
game-side behavior, not an OS/driver-side one.
"""

DEFAULT_DEADZONE = 0.05
DEFAULT_EXPO = 1.0

RUDDER_MIN = 0
RUDDER_MAX = 32767
RUDDER_CENTRE = (RUDDER_MIN + RUDDER_MAX) // 2


def normalize(value, info_min, info_max):
    """Map value from [info_min, info_max] to [0.0, 1.0]."""
    span = info_max - info_min
    if span == 0:
        return 0.0
    return (value - info_min) / span


def fold_rudder(
    lt_value, lt_min, lt_max,
    rt_value, rt_min, rt_max,
    deadzone=DEFAULT_DEADZONE, expo=DEFAULT_EXPO, invert=False,
):
    """Return the folded rudder value in RUDDER_MIN..RUDDER_MAX (unipolar)."""
    x = normalize(rt_value, rt_min, rt_max) - normalize(lt_value, lt_min, lt_max)

    if abs(x) < deadzone:
        x = 0.0
    else:
        sign = 1.0 if x > 0 else -1.0
        x = sign * ((abs(x) - deadzone) / (1.0 - deadzone)) ** expo

    if invert:
        x = -x

    value = int((x + 1.0) / 2.0 * RUDDER_MAX)
    return max(RUDDER_MIN, min(RUDDER_MAX, value))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rudder.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add res/rudder.py tests/test_rudder.py
git commit -m "feat: port rudder fold from Linux source (verbatim, OS-independent)"
```

---

### Task 3: Right-stick-to-mouse velocity math

**Files:**
- Create: `res/mouse_look.py`
- Test: `tests/test_mouse_look.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `res.mouse_look.DEFAULT_DEADZONE` (`0.1`), `DEFAULT_GAIN` (`1.0`), `DEFAULT_EXPO` (`0.0`), `REL_XY_SCALING` (`60.0`), `DEFAULT_RATE_HZ` (`60.0`); `normalize(value, info_min, info_max)` (float, `-1.0..1.0`); `flatten_deadzone(x, deadzone)` (float); `apply_expo(x, expo)` (float); `stick_to_velocity(value, info_min, info_max, deadzone=DEFAULT_DEADZONE, gain=DEFAULT_GAIN, expo=DEFAULT_EXPO)` (float); `RelAccumulator(rate_hz=DEFAULT_RATE_HZ)` class with `.tick(velocity)` -> int; `MouseLookState()` class with `.set(vx=None, vy=None)` and `.get()` -> `(vx, vy)` tuple.
- **Not produced by this task** (deliberately dropped, belongs to the Windows I/O plan): `mouse_tick_loop` — the Linux version's loop function that calls `from evdev import ecodes as e` and writes to a `ui_mouse` uinput device. Its logic (drive `RelAccumulator` at a fixed rate, write when nonzero) is a spec for the later plan to reimplement against `SendInput`, not code to port here.

- [ ] **Step 1: Write the failing test**

`tests/test_mouse_look.py` (ported verbatim — none of the existing tests touch `mouse_tick_loop`, so nothing needs trimming here):
```python
import unittest

from res.mouse_look import (
    RelAccumulator,
    apply_expo,
    flatten_deadzone,
    normalize,
    stick_to_velocity,
)


class TestNormalize(unittest.TestCase):
    def test_centre_is_zero(self):
        self.assertAlmostEqual(normalize(0, -32768, 32767), 0.0, places=3)

    def test_max_is_one(self):
        self.assertAlmostEqual(normalize(32767, -32768, 32767), 1.0, places=3)

    def test_min_is_negative_one(self):
        self.assertAlmostEqual(normalize(-32768, -32768, 32767), -1.0, places=3)


class TestFlattenDeadzone(unittest.TestCase):
    def test_inside_deadzone_is_zero(self):
        self.assertEqual(flatten_deadzone(0.05, deadzone=0.1), 0.0)

    def test_deadzone_edge_rescales_to_full_range(self):
        self.assertAlmostEqual(flatten_deadzone(0.5, deadzone=0.1), 0.4444444, places=5)

    def test_negative_side_mirrors_positive(self):
        pos = flatten_deadzone(0.5, deadzone=0.1)
        neg = flatten_deadzone(-0.5, deadzone=0.1)
        self.assertAlmostEqual(neg, -pos)


class TestApplyExpo(unittest.TestCase):
    def test_zero_expo_is_linear(self):
        self.assertEqual(apply_expo(0.5, expo=0.0), 0.5)

    def test_full_expo_is_cubic(self):
        self.assertAlmostEqual(apply_expo(0.5, expo=1.0), 0.125)

    def test_zero_input_is_zero(self):
        self.assertEqual(apply_expo(0.0, expo=0.5), 0.0)


class TestStickToVelocity(unittest.TestCase):
    def test_centred_stick_is_zero(self):
        self.assertAlmostEqual(stick_to_velocity(0, -32768, 32767), 0.0, places=2)

    def test_full_deflection_is_near_one(self):
        self.assertAlmostEqual(stick_to_velocity(32767, -32768, 32767), 1.0, places=2)


class TestRelAccumulator(unittest.TestCase):
    def test_zero_velocity_produces_zero(self):
        acc = RelAccumulator(rate_hz=60.0)
        self.assertEqual(acc.tick(0.0), 0)

    def test_full_velocity_matches_scaling_constant(self):
        acc = RelAccumulator(rate_hz=60.0)
        for _ in range(5):
            self.assertEqual(acc.tick(1.0), 60)

    def test_partial_velocity_converges_to_expected_average(self):
        acc = RelAccumulator(rate_hz=60.0)
        velocity = 0.3
        counts = [acc.tick(velocity) for _ in range(100)]
        expected_total = velocity * 60.0 * 100
        self.assertLess(abs(sum(counts) - expected_total), 1.0)

    def test_recenter_resets_remainder(self):
        acc = RelAccumulator(rate_hz=60.0)
        acc.tick(0.3)
        self.assertEqual(acc.tick(0.0), 0)

        fresh = RelAccumulator(rate_hz=60.0)
        after_recentre = [acc.tick(0.3) for _ in range(10)]
        from_fresh = [fresh.tick(0.3) for _ in range(10)]
        self.assertEqual(after_recentre, from_fresh)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mouse_look.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.mouse_look'`

- [ ] **Step 3: Write the implementation**

`res/mouse_look.py`:
```python
"""Translate right-stick deflection into rate-based relative mouse motion,
matching the Linux source project's port of input-remapper's
AbsToRelHandler behaviour (verified there against its source:
abs_to_rel_handler.py / axis_transform.py, package inputremapper 2.2.1).

This module is the pure math only. Driving an actual mouse device at a
fixed tick rate is OS-specific (the Linux source used a uinput write
loop; Windows uses SendInput) and belongs to the Windows I/O layer, not
here — see MouseLookState/RelAccumulator's docstrings for what that
layer is expected to do with these pieces.
"""

import math
import threading

DEFAULT_DEADZONE = 0.1
DEFAULT_GAIN = 1.0
DEFAULT_EXPO = 0.0
REL_XY_SCALING = 60.0
DEFAULT_RATE_HZ = 60.0


def normalize(value, info_min, info_max):
    """Map value from [info_min, info_max] to [-1.0, 1.0]."""
    half_range = (info_max - info_min) / 2.0
    if half_range == 0:
        return 0.0
    middle = half_range + info_min
    return (value - middle) / half_range


def flatten_deadzone(x, deadzone):
    """Collapse values inside the deadzone to 0, rescale the rest to -1..1."""
    if abs(x) <= deadzone:
        return 0.0
    sign = x / abs(x)
    return (x - deadzone * sign) / (1.0 - deadzone)


def apply_expo(x, expo):
    """Cubic expo curve: expo=0 linear, expo=1 fully cubic (soft centre)."""
    if expo == 0 or x == 0:
        return x
    d = 1.0 - expo
    return d * x + (1.0 - d) * x**3


def stick_to_velocity(
    value, info_min, info_max,
    deadzone=DEFAULT_DEADZONE, gain=DEFAULT_GAIN, expo=DEFAULT_EXPO,
):
    """Return a -1..1 velocity for the current stick position."""
    x = normalize(value, info_min, info_max)
    x = flatten_deadzone(x, deadzone)
    x = apply_expo(x, expo)
    return x * gain


class RelAccumulator:
    """Converts a -1..1 velocity into per-tick relative-motion counts,
    carrying fractional remainder across ticks so slow motion still moves
    the cursor over time. One instance per axis."""

    def __init__(self, rate_hz=DEFAULT_RATE_HZ):
        rate_compensation = DEFAULT_RATE_HZ / rate_hz
        self._weight = REL_XY_SCALING * rate_compensation
        self._remainder = 0.0

    def tick(self, velocity):
        if velocity == 0:
            self._remainder = 0.0
            return 0
        scaled = velocity * self._weight + self._remainder
        count = int(scaled)
        self._remainder = math.fmod(scaled, 1)
        return count


class MouseLookState:
    """Lock-protected last-seen right-stick velocity, written by the main
    event-read thread and read by a mouse-tick thread the Windows I/O
    layer provides (which will drive SendInput at a fixed rate, the way
    the Linux source's mouse_tick_loop drove a uinput write loop)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._vx = 0.0
        self._vy = 0.0

    def set(self, vx=None, vy=None):
        with self._lock:
            if vx is not None:
                self._vx = vx
            if vy is not None:
                self._vy = vy

    def get(self):
        with self._lock:
            return self._vx, self._vy
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mouse_look.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add res/mouse_look.py tests/test_mouse_look.py
git commit -m "feat: port right-stick-to-mouse velocity math (drops evdev-specific tick loop)"
```

---

### Task 4: Combo mapping tables

**Files:**
- Create: `res/combos.py`
- Test: `tests/test_combos.py`

**Interfaces:**
- Consumes: `res.logical_input.{SOUTH, NORTH, EAST, WEST, TL, TR, FACE_BUTTONS, HAT_X, HAT_Y, UP, DOWN, LEFT, RIGHT, DIRECTIONS, dpad_direction_for}` (Task 1).
- Produces: `res.combos.{WEST, NORTH, SOUTH, EAST, TL, TR, FACE_BUTTONS, HAT_X, HAT_Y, UP, DOWN, LEFT, RIGHT, DIRECTIONS, dpad_direction_for}` (re-exported from `logical_input`, same names as the Linux source's `combos.py` so `combo_detector.py` and its tests need no changes beyond the import source); `TABLE_1` (dict, `(face_button, direction) -> glyph str`, 16 entries); `TABLE_2` (dict, `(direction, face_button) -> glyph str`, 16 entries); `TABLE_3` (dict, `face_button -> face_button`, 4 entries, self-mapped).

- [ ] **Step 1: Write the failing test**

`tests/test_combos.py` (ported from the Linux source; `test_specific_ported_mappings` is rewritten to check glyph strings instead of `evdev.ecodes.KEY_*`, since this project has no evdev dependency — the mapping intent is identical, only the representation changed):
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_combos.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.combos'`

- [ ] **Step 3: Write the implementation**

`res/combos.py`:
```python
"""Static combo-mapping tables — the runtime mirror of the Linux source
project's docs/button_combo_mappings.md. Keep the two in sync; this
module is data, not logic. See res/combo_detector.py for the detection
state machine that consumes these tables.

Ported from the Linux source's res/combos.py. That version keyed
everything off evdev.ecodes (Linux kernel input-event-code integers);
this version uses res.logical_input's plain-string roles instead, since
evdev doesn't exist on Windows. Keyboard-macro outputs (TABLE_1/TABLE_2
values) are plain glyph strings rather than evdev KEY_* codes — a later
Windows I/O plan's output layer turns a glyph into a SendInput
keystroke.
"""

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
    TL,
    TR,
    UP,
    WEST,
    dpad_direction_for,
)

__all__ = [
    "WEST", "NORTH", "SOUTH", "EAST", "TL", "TR", "FACE_BUTTONS",
    "HAT_X", "HAT_Y", "UP", "DOWN", "LEFT", "RIGHT", "DIRECTIONS",
    "dpad_direction_for", "TABLE_1", "TABLE_2", "TABLE_3",
]

# Table 1 -- button held, then D-pad direction tapped.
TABLE_1 = {
    (WEST, UP): "Q",
    (WEST, RIGHT): "W",
    (WEST, DOWN): "S",
    (WEST, LEFT): "A",
    (NORTH, UP): "E",
    (NORTH, RIGHT): "R",
    (NORTH, DOWN): "F",
    (NORTH, LEFT): "D",
    (SOUTH, UP): "T",
    (SOUTH, RIGHT): "Y",
    (SOUTH, DOWN): "H",
    (SOUTH, LEFT): "G",
    (EAST, UP): "U",
    (EAST, RIGHT): "I",
    (EAST, DOWN): "K",
    (EAST, LEFT): "J",
}

# Table 2 -- D-pad direction held, then button tapped.
TABLE_2 = {
    (UP, NORTH): "O",
    (UP, EAST): "P",
    (UP, SOUTH): "Ö",
    (UP, WEST): "L",
    (DOWN, NORTH): "Z",
    (DOWN, EAST): "X",
    (DOWN, SOUTH): "C",
    (DOWN, WEST): "V",
    (LEFT, NORTH): "B",
    (LEFT, EAST): "N",
    (LEFT, SOUTH): "M",
    (LEFT, WEST): ",",
    (RIGHT, NORTH): ".",
    (RIGHT, EAST): "-",
    (RIGHT, SOUTH): "Ä",
    (RIGHT, WEST): "Å",
}

# Table 3 -- button + TR + TL, self-mapped.
TABLE_3 = {
    WEST: WEST,
    NORTH: NORTH,
    SOUTH: SOUTH,
    EAST: EAST,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_combos.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add res/combos.py tests/test_combos.py
git commit -m "feat: port combo mapping tables with glyph-string outputs (no evdev)"
```

---

### Task 5: Combo detector state machine

**Files:**
- Create: `res/combo_detector.py`
- Test: `tests/test_combo_detector.py`

**Interfaces:**
- Consumes: `res.combos.{DIRECTIONS, FACE_BUTTONS, TABLE_1, TABLE_2, TABLE_3, TL, TR}` (Task 4).
- Produces: `res.combo_detector.KEYBOARD` (str, `"keyboard"`), `GAMEPAD` (str, `"gamepad"`), `Fire` (namedtuple, fields `device`, `code`); `ComboDetector()` class with `.on_face_button(code, pressed)` -> `list[Fire]`, `.on_dpad_direction(direction, pressed)` -> `list[Fire]`, `.on_shoulder(code, pressed)` -> `(list[Fire], bool forward)`.

- [ ] **Step 1: Write the failing test**

`tests/test_combo_detector.py` (ported verbatim — this state machine already never touched evdev; only `res.combos`'s import source changed in Task 4, and this file imports from `res.combos`, not `evdev`, so no test content changes):
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_combo_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'res.combo_detector'`

- [ ] **Step 3: Write the implementation**

`res/combo_detector.py` (ported verbatim from the Linux source — this state machine never imported evdev; only the module it imports constants from changed, in Task 4):
```python
"""Runtime detector for the chorded button macros defined in
res/combos.py.

Pure logic: consumes button/D-pad press-release edges, returns a list of
Fire actions to emit. Does not touch any OS input/output API directly,
so it's unit testable without a real device or Windows machine — a
later Windows I/O plan provides the adapter that feeds it real pygame
events and dispatches its Fires to vJoy/SendInput.
"""

from collections import namedtuple

from res.combos import DIRECTIONS, FACE_BUTTONS, TABLE_1, TABLE_2, TABLE_3, TL, TR

KEYBOARD = "keyboard"
GAMEPAD = "gamepad"

Fire = namedtuple("Fire", ["device", "code"])

_FACE_BUTTON_SET = set(FACE_BUTTONS)


class ComboDetector:
    """Tracks starter/completer state for the 8 combo-eligible inputs (4
    face buttons + 4 D-pad directions) and the TL/TR shoulder pair.

    Role-lock rule: an input becomes either a starter or a completer on its
    own press, whichever it first satisfies, and keeps that role until its
    own release — it never retroactively switches roles mid-hold, even if
    the state around it changes.
    """

    def __init__(self):
        self._armed_starters = set()
        self._locked_completers = set()
        self._tl_down = False
        self._tr_down = False

    def _release(self, code):
        self._armed_starters.discard(code)
        self._locked_completers.discard(code)

    def _on_press(self, code, complementary, lookup):
        fires = []
        for other in complementary:
            key = lookup(other)
            if key is not None:
                fires.append(Fire(KEYBOARD, key))

        if fires:
            self._locked_completers.add(code)
        else:
            self._armed_starters.add(code)

        return fires

    def on_face_button(self, code, pressed):
        if not pressed:
            self._release(code)
            return []
        return self._on_press(
            code,
            complementary=self._armed_starters & DIRECTIONS,
            lookup=lambda direction: TABLE_2.get((direction, code)),
        )

    def on_dpad_direction(self, direction, pressed):
        if not pressed:
            self._release(direction)
            return []
        return self._on_press(
            direction,
            complementary=self._armed_starters & _FACE_BUTTON_SET,
            lookup=lambda button: TABLE_1.get((button, direction)),
        )

    def on_shoulder(self, code, pressed):
        """code is TL or TR. Returns (fires, forward): forward is True if
        the raw press/release should still pass through to the output
        gamepad untouched (no face button currently held)."""
        face_buttons_held = bool(self._armed_starters & _FACE_BUTTON_SET)

        if code == TL:
            self._tl_down = pressed
        elif code == TR:
            self._tr_down = pressed

        if not face_buttons_held:
            return [], True

        fires = []
        if pressed and self._tl_down and self._tr_down:
            for button in self._armed_starters & _FACE_BUTTON_SET:
                out = TABLE_3.get(button)
                if out is not None:
                    fires.append(Fire(GAMEPAD, out))

        return fires, False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_combo_detector.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: PASS, 52 tests total (7 + 10 + 14 + 11 + 10, from Tasks 1-5)

- [ ] **Step 6: Commit**

```bash
git add res/combo_detector.py tests/test_combo_detector.py
git commit -m "feat: port combo detector state machine (verbatim logic, no evdev)"
```

---

## Self-Review Notes

- **Spec coverage:** rudder fold (Task 2), right-stick-to-mouse math minus the evdev-specific tick loop (Task 3), combo tables (Task 4), combo detection state machine (Task 5), and the new abstraction they all needed since `evdev.ecodes` isn't available on Windows (Task 1) — all four Linux-source modules this plan claimed to port are covered.
- **Deliberately not covered by this plan** (belongs to the Windows I/O layer plan instead, since it requires pygame/vJoy/SendInput which can't be verified without a Windows machine): device scanning/enumeration, controller profiles (physical button/axis index -> logical role mappings for the 8BitDo pad and DS4), `mouse_tick_loop`'s SendInput-driven replacement, vJoy gamepad output, keyboard-macro glyph -> SendInput keystroke translation, the console controller-picker, config persistence for the remembered controller choice, and the installer/packaging plan.
- **Placeholder scan:** no TBD/TODO/"handle appropriately" language in any step; every code block is complete, runnable code.
- **Type/name consistency:** `res.logical_input`'s names (`SOUTH`, `NORTH`, `EAST`, `WEST`, `TL`, `TR`, `FACE_BUTTONS`, `HAT_X`, `HAT_Y`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `DIRECTIONS`, `dpad_direction_for`) are re-exported unchanged through `res.combos` (Task 4), and `res.combo_detector` (Task 5) imports exactly those names from `res.combos` — matches the Linux source's import shape so anyone who's read that codebase recognizes this one, with only the vocabulary's origin (strings vs. evdev ints) changed.
