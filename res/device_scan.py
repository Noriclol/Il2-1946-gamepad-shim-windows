"""Enumerate connected controllers via pygame, match them against known
profiles (res.profiles), and run the boot-time console picker.

pygame.joystick wraps SDL2, giving uniform enumeration across
DirectInput- and XInput-backed devices -- chosen over an XInput-only
library because PlayStation pads don't speak XInput at all (see
docs/superpowers/plans/2026-08-31-windows-port-roadmap.md).

enumerate_controllers() is the only function here that touches the real
pygame package, and does so via a lazy import so this module -- and
choose_controller()'s picker logic -- stay testable on a machine with no
pygame installed at all.
"""

from dataclasses import dataclass

from res.profiles import PROFILES, find_profile


@dataclass(frozen=True)
class DetectedController:
    """index: pygame joystick index at enumeration time -- NOT stable
    across reconnects, callers persist the name (see res.config), not
    the index.
    name: pygame Joystick.get_name().
    profile: the matched ControllerProfile from res.profiles, or None if
    unprofiled."""

    index: int
    name: str
    profile: object


class NoProfileError(Exception):
    """Raised when the user selects a controller with no matching
    ControllerProfile -- see res.profiles.find_profile."""


def enumerate_controllers():
    """Return a DetectedController for every currently connected joystick
    pygame can see. Requires pygame.joystick to already be initialised by
    the caller (pygame.init(); pygame.joystick.init()) -- this function
    doesn't own that lifecycle since a longer-lived caller (res/main.py,
    not built by this plan) needs pygame initialised for the whole
    session, not just this one call."""
    import pygame

    controllers = []
    for i in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(i)
        name = joystick.get_name()
        controllers.append(DetectedController(index=i, name=name, profile=find_profile(name)))
    return controllers


def choose_controller(controllers, remembered_name=None, prompt=input, output=print):
    """Pure selection logic for the boot-time console picker, with
    input/output injected for testability.

    controllers: non-empty list of DetectedController (callers handle the
    empty "no controllers found" case before calling this).
    remembered_name: the previously-chosen controller's name, or None.
    Pre-selected as the default (pressing Enter with no input picks it)
    if still present in controllers; otherwise ignored.
    prompt: callable(message) -> str, defaults to the builtin input.
    output: callable(message) -> None, defaults to the builtin print.

    Returns the chosen DetectedController. Raises NoProfileError if the
    chosen controller has no matching profile.
    """
    default_index = None
    for controller in controllers:
        marker = ""
        if remembered_name is not None and controller.name == remembered_name:
            default_index = controller.index
            marker = "  [last used]"
        output(f"  [{controller.index}] {controller.name}{marker}")

    if default_index is not None:
        raw = prompt(f"Press Enter to use [{default_index}], or type a number: ")
    else:
        raw = prompt(f"Select controller [0-{len(controllers) - 1}]: ")

    raw = raw.strip()
    chosen_index = default_index if (raw == "" and default_index is not None) else int(raw)

    chosen = next(c for c in controllers if c.index == chosen_index)
    if chosen.profile is None:
        supported = ", ".join(alias for p in PROFILES for alias in p.name_match) or "none"
        raise NoProfileError(
            f"No button profile for {chosen.name!r}. Supported controllers: {supported}."
        )
    return chosen
