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
