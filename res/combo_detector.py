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
