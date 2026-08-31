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
