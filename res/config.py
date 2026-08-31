"""Persist the boot-time controller picker's remembered choice.

Plain JSON file, not any platform-specific config API -- keeps this
testable without a real Windows profile directory. The caller (a later
res/main.py, not built by this plan) decides the real path (e.g.
%APPDATA%\\IL2Shim\\config.json on Windows); this module only needs a
path handed to it.
"""

import json
from pathlib import Path


def load_last_choice(path):
    """Return the remembered controller name, or None if no config file
    exists yet, or it's unreadable/malformed."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("last_controller_name")


def save_last_choice(path, controller_name):
    """Write the chosen controller's name to path, creating parent
    directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"last_controller_name": controller_name}))
