"""Windows mouse-motion injection via SendInput, driving res.mouse_look's
fixed-rate mouse-tick loop.

No virtual mouse *device* is created. SendInput injects synthetic
relative motion straight into the OS input stream; IL-2 sees it as if
it came from the real mouse. This differs from the Linux source
project's build_mouse_uinput, which needed a real virtual uinput device
only because udev/libinput/X11 refuse to treat a REL_X/REL_Y stream as
a pointer at all without one -- a Linux-specific classification gate
with no Windows equivalent, so there's nothing to carbon-copy for the
mouse (see res/vjoy_output.py for the one output split that *was*
carbon-copied, and why).

mouse_tick_loop() lives here rather than in res.mouse_look because that
module is pure math only (see its own docstring) -- driving a real
device at a fixed rate is the Windows I/O layer's job. It mirrors the
Linux source's mouse_tick_loop (res/mouse_look.py there), but calls
send_relative_mouse_move() instead of writing evdev REL events.

ctypes.windll only exists on Windows. The INPUT/MOUSEINPUT struct
definitions below use only plain ctypes/ctypes.wintypes, which are
importable on any platform, so this module stays importable (and
mouse_tick_loop's timing/accumulation logic testable via the injected
send_move callable) without Windows. Only send_relative_mouse_move()
touches ctypes.windll, and it does so lazily.

Keyboard side (send_scancode_key/tap_scancode_key/SCANCODE_MAP): fires
the res.combo_detector chorded macros (res/combos.py's TABLE_1/TABLE_2
glyph outputs) as real keystrokes. Uses KEYEVENTF_SCANCODE
(layout-independent -- addresses a physical key position, same as
evdev's KEY_* convention did on the Linux source project) rather than
VK-code SendInput, per res/combos.py's module docstring: VK codes have
no single constant for the six Nordic/punctuation glyphs (Å, Ä, Ö, `,`
`.` `-`) independent of the active Windows keyboard layout, so a
scancode table addressing the same US-layout physical positions the
Linux source's evdev KEY_* constants named is used instead.
"""

import time
from ctypes import Structure, Union, byref, c_size_t, sizeof, wintypes

from res.mouse_look import DEFAULT_RATE_HZ, RelAccumulator

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

# US-layout Set 1 (PC/AT) hardware make scancodes, keyed by the same
# glyph strings res/combos.py's TABLE_1/TABLE_2 use as outputs.
# KEYEVENTF_SCANCODE addresses these as physical key positions
# regardless of the active Windows keyboard layout. The six
# Nordic/punctuation glyphs use the physical-key equivalences recorded
# in res/combos.py's module docstring (e.g. Å sits at the evdev
# KEY_LEFTBRACE position under a Swedish layout) translated to their
# Set 1 scancode.
SCANCODE_MAP = {
    "Q": 0x10, "W": 0x11, "E": 0x12, "R": 0x13, "T": 0x14,
    "Y": 0x15, "U": 0x16, "I": 0x17, "O": 0x18, "P": 0x19,
    "A": 0x1E, "S": 0x1F, "D": 0x20, "F": 0x21, "G": 0x22,
    "H": 0x23, "J": 0x24, "K": 0x25, "L": 0x26,
    "Z": 0x2C, "X": 0x2D, "C": 0x2E, "V": 0x2F, "B": 0x30,
    "N": 0x31, "M": 0x32,
    "Å": 0x1A,  # KEY_LEFTBRACE position
    "Ä": 0x28,  # KEY_APOSTROPHE position
    "Ö": 0x27,  # KEY_SEMICOLON position
    ",": 0x33,  # KEY_COMMA position
    ".": 0x34,  # KEY_DOT position
    "-": 0x0C,  # KEY_MINUS position
}

DEFAULT_TAP_HOLD_SECONDS = 0.05

# ULONG_PTR: an unsigned int the size of a pointer. Must match on 32-
# and 64-bit Windows for MOUSEINPUT.dwExtraInfo (and so the whole
# struct's layout) to line up with what SendInput expects.
ULONG_PTR = c_size_t


class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _InputUnion(Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(Structure):
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _InputUnion)]


def send_relative_mouse_move(dx, dy):
    """Inject one relative mouse-move event via SendInput. No-op if both
    deltas are 0 -- matches RelAccumulator.tick, which already returns 0
    for a centred stick, so callers don't need to check first. Imports
    ctypes.windll lazily so this module stays importable on any
    platform; not covered by this project's unit tests, same reasoning
    as res.vjoy_output.build_vjoy_device -- needs a real Windows session
    to verify at all."""
    if dx == 0 and dy == 0:
        return

    import ctypes

    inp = INPUT(
        type=INPUT_MOUSE,
        mi=MOUSEINPUT(
            dx=dx, dy=dy, mouseData=0, dwFlags=MOUSEEVENTF_MOVE, time=0, dwExtraInfo=0
        ),
    )
    ctypes.windll.user32.SendInput(1, byref(inp), sizeof(inp))


def send_scancode_key(scancode, key_up=False):
    """Inject one keyboard key-down or key-up via SendInput, addressing
    scancode as a physical key position (KEYEVENTF_SCANCODE) rather than
    a layout-mapped virtual key -- see module docstring for why. Imports
    ctypes.windll lazily so this module stays importable on any
    platform; not covered by this project's unit tests, same reasoning
    as send_relative_mouse_move -- needs a real Windows session to
    verify at all."""
    import ctypes

    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    inp = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(wVk=0, wScan=scancode, dwFlags=flags, time=0, dwExtraInfo=0),
    )
    ctypes.windll.user32.SendInput(1, byref(inp), sizeof(inp))


def tap_scancode_key(scancode, send_key=send_scancode_key, hold_seconds=DEFAULT_TAP_HOLD_SECONDS):
    """Press then release scancode, holding hold_seconds in between so the
    game's input polling reliably sees the keypress. send_key is
    injected (defaulting to the real SendInput call) so this is testable
    without ctypes.windll -- a test double records the (scancode,
    key_up) pairs instead. Meant to run off the main input-poll thread
    (see res.main.dispatch_fire) since it blocks for hold_seconds."""
    send_key(scancode, key_up=False)
    time.sleep(hold_seconds)
    send_key(scancode, key_up=True)


def mouse_tick_loop(state, stop_event, rate_hz=DEFAULT_RATE_HZ, send_move=send_relative_mouse_move):
    """Background-thread target: injects relative mouse motion at a fixed
    rate for as long as the right stick is deflected. Runs until
    stop_event is set. send_move is injected (defaulting to the real
    SendInput call) so this loop's timing/accumulation logic is testable
    without ctypes.windll -- a test double records calls instead."""
    acc_x = RelAccumulator(rate_hz)
    acc_y = RelAccumulator(rate_hz)
    interval = 1.0 / rate_hz

    while not stop_event.is_set():
        start = time.monotonic()
        vx, vy = state.get()
        dx = acc_x.tick(vx)
        dy = acc_y.tick(vy)
        send_move(dx, dy)
        elapsed = time.monotonic() - start
        time.sleep(max(0.0, interval - elapsed))
