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
