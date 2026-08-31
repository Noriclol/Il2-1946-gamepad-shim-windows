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

TABLE_1/TABLE_2 use three non-ASCII glyphs (Å, Ä, Ö) plus three
punctuation glyphs (`,` `.` `-`) that carry hard-won context from the
Linux source project, recorded here so it isn't lost: the Linux
source's physical-key choices for these six glyphs assumed a Swedish
(`se`) X11 keyboard layout, combined with evdev's convention that
KEY_* codes name US-layout *physical positions* regardless of the
active layout (see the Linux source's `res/combos.py` and
`docs/findings.md`). Concretely, under that Swedish layout, the
physical keys that produce these glyphs are: Å -> KEY_LEFTBRACE,
Ä -> KEY_APOSTROPHE, Ö -> KEY_SEMICOLON, `,` -> KEY_COMMA,
`.` -> KEY_DOT, `-` -> KEY_MINUS.

Whoever writes the Windows glyph->keystroke translator (Plan 2's
`res/sendinput_output.py`) must explicitly decide between two
different SendInput strategies, because they need different glyph
tables:
  - Virtual-key-code SendInput (layout-aware): the OS maps a VK code
    to a physical key using the *active* Windows keyboard layout.
    Glyph->VK is straightforward for plain letters, but ambiguous for
    Swedish-specific punctuation/Nordic glyphs like the six above —
    there's no single VK constant for "Å" independent of layout.
  - Scancode-based SendInput (KEYEVENTF_SCANCODE, layout-independent):
    addresses a physical key position regardless of the active
    layout, same as evdev did. This needs the same
    US-layout-physical-position table the Linux source used (the six
    mappings above), not a fresh one derived from VK codes.
Do not assume one strategy without deciding explicitly — mixing them
will silently send the wrong physical key for the Nordic glyphs.
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
