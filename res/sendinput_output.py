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
"""

import time
from ctypes import Structure, Union, byref, c_size_t, sizeof, wintypes

from res.mouse_look import DEFAULT_RATE_HZ, RelAccumulator

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001

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


class _InputUnion(Union):
    _fields_ = [("mi", MOUSEINPUT)]


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
