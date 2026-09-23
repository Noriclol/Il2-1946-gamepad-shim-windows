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

PROFILE_DS4's face buttons and shoulder buttons ARE now verified, from
a real DS4 diagnostic run (scripts/windows_diagnostics.py) on Windows,
2026-09-23: SOUTH=0, EAST=1, WEST=2, NORTH=3, TL=9, TR=10. That run's
pad reported 0 hats -- its D-pad is exposed as extra buttons instead
(D-pad UP verified as button 15), so hat_index stays None; D-pad-driven
combos aren't wired up yet as a result. The same run's pygame device
name was "PS4 Controller" (USB), not "Wireless Controller" (the
Bluetooth name this project's name_match was written against) -- hence
name_match now accepts multiple aliases per profile.
"""

from dataclasses import dataclass, field

from res.logical_input import EAST, NORTH, SOUTH, TL, TR, WEST

AXIS_X = "X"
AXIS_Y = "Y"
AXIS_LT = "LT"
AXIS_RT = "RT"
AXIS_RX = "RX"
AXIS_RY = "RY"

REQUIRED_AXIS_ROLES = (AXIS_X, AXIS_Y, AXIS_LT, AXIS_RT, AXIS_RX, AXIS_RY)


@dataclass(frozen=True)
class ControllerProfile:
    """name_match: a tuple of lowercase substrings, any of which matches
    against pygame's Joystick.get_name() (case-insensitive) -- the same
    approach the Linux source's scan_for_pad used (MATCH = "8bitdo"),
    extended to a tuple since the same physical pad can report different
    names depending on connection type (e.g. a DS4 reports "Wireless
    Controller" over Bluetooth but "PS4 Controller" over USB).

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

    name_match: tuple
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
    name_match=("8bitdo",),
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
    name_match=("wireless controller", "ps4 controller"),
    axis_map={
        AXIS_X: 0,
        AXIS_Y: 1,
        AXIS_RX: 2,
        AXIS_RY: 3,
        AXIS_LT: 4,
        AXIS_RT: 5,
    },
    button_map={
        SOUTH: 0,
        EAST: 1,
        WEST: 2,
        NORTH: 3,
        TL: 9,
        TR: 10,
    },
    button_mapping_verified=True,
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
        if any(alias in lowered for alias in profile.name_match):
            return profile
    return None
