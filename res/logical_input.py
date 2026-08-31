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
