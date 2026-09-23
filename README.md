# IL-2 1946 Gamepad Shim (Windows)

A Windows port of [`Il2-1946-gamepad-shim`](https://github.com/) (local: `~/Projects/Il2-1946-gamepad-shim`), a shim that lets an 8BitDo Ultimate/Pro 2 pad (or a PlayStation DualShock 4) drive IL-2 Sturmovik 1946. It folds the two analog triggers into one bidirectional rudder axis, translates right-stick deflection into mouse-look motion, and adds chorded button macros the game can't bind natively.

The Linux source project runs the game under Wine/Proton and solves a hard device-enumeration problem (making the shim's virtual device outrank the physical one). This Windows port runs the game natively and sidesteps that problem entirely: [vJoy](http://vjoystick.sourceforge.net/) creates a persistent virtual DirectInput device that IL-2 binds to directly, so the physical pad's own presence in the device list never matters.

## Status

Portable logic core (rudder fold, mouse-look math, chorded-combo detection) and I/O-layer groundwork (controller profiles, device scanning, config persistence, vJoy output mapping) are implemented and unit tested. `res/main.py` now wires a minimal DS4-only pipeline — left-stick + trigger passthrough, rudder fold, right-stick mouse-look, and the four face buttons + TL/TR — onto two real vJoy devices and SendInput mouse motion, verified against a real DS4's pygame button indices (see `res/profiles.py`). Not yet built: the keyboard-macro half of `res/sendinput_output.py` (the VK-code-vs-scancode decision needs testing on real Windows hardware), D-pad-driven combos, and an installer. See `docs/superpowers/plans/` for the implementation plans and `docs/superpowers/plans/2026-08-31-windows-port-roadmap.md` for what's left and why it's sequenced this way.

## For a Windows tester: try the shim itself (DS4 only, for now)

This needs the [vJoy driver](http://vjoystick.sourceforge.net/) installed and **two** of its devices configured **before** running the shim, one time only. The rudder is deliberately its own separate device rather than an axis on the gamepad device — carbon-copying a structural fix from the Linux source project, where a shared gamepad-shaped device corrupted the rudder signal under Wine; see `res/vjoy_output.py` for the full reasoning.

1. Install the vJoy driver from the link above (it's a community-signed driver — if Windows refuses it, you may need to enable test-signing mode; see the roadmap doc).
2. Run `vJoyConf` (installed alongside the driver) and configure:
   - **Device #1**: axes **X, Y** and at least **6 buttons**. Leave everything else default.
   - **Device #2**: a single axis (any one, e.g. X) and no buttons.
   Enable both devices.
3. Install [Python 3.12](https://www.python.org/downloads/) (check "Add python.exe to PATH" during install) if you haven't already.
4. Download this repo as a zip, extract it, and double-click `launch.bat` in the extracted folder.
5. It'll ask you to pick your controller from a list (press Enter for the default) — then moving the left stick and pressing South/East/West/North/TL/TR should move vJoy's device #1 live, pulling either trigger should move device #2's axis, and moving the right stick should move the real mouse cursor. You can check the vJoy devices in Windows' own "Set up USB game controllers" (`joy.cpl`) or in `vJoyConf`'s monitor tab.

Keyboard-macro combos aren't wired up yet, so those won't do anything. Press Ctrl+C in the console window to stop.

## For a Windows tester: run the diagnostics

If you have a Windows machine with the controller(s) plugged in — and ideally IL-2 1946 installed — this project needs a few things checked that can only be verified on real Windows hardware. `scripts/windows_diagnostics.py` walks through all of them and writes everything to `log.txt` at the repo root.

**Easy way (no typing):** install [Python 3.12](https://www.python.org/downloads/) (check "Add python.exe to PATH" during install), download this repo as a zip and extract it, then double-click `run_diagnostics.bat` in the extracted folder. It sets everything up and runs the checks for you.

**Manual way:**

```bat
git clone <this repo>
cd Il2-1946-gamepad-shim-windows
python -m venv venv
venv\Scripts\pip install pygame pyvjoy
venv\Scripts\python scripts\windows_diagnostics.py
```

`pyvjoy` also needs the [vJoy driver](http://vjoystick.sourceforge.net/) itself installed separately — `pip install` alone won't get you that. If you don't have it installed yet, that's fine: the script detects it's missing, says so in the log, and moves on to the other checks rather than failing.

It'll print everything to the screen as it goes and ask you to press a few buttons and move the sticks/triggers along the way — just follow the prompts, there's no rush between them. When it's done, send the resulting `log.txt` back.

It only reads — no registry writes, no install steps, and no keystrokes or mouse motion get sent to any other window.

## Running the tests

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/pytest -q
```

No physical controller, pygame, or vJoy driver is required to run the test suite — every module that touches real device/driver I/O does so behind a lazy import inside the one function that needs it, so the rest of each module (and its tests) stays importable and testable without that dependency installed.

## Layout

- `res/` — the shim's source code.
- `tests/` — its test suite (mirrors `res/` file-for-file).
- `docs/superpowers/plans/` — implementation plans, written and executed one at a time; each records what it built, what it deliberately deferred, and why.

## Controller profiles

`res/profiles.py` defines `ControllerProfile`: a dataclass mapping a physical controller's pygame axis/button/hat indices onto the logical roles the rest of the shim operates on (`res/rudder.py`'s `LT`/`RT`, `res/mouse_look.py`'s `RX`/`RY`, `res/logical_input.py`'s button roles). Two profiles ship: `PROFILE_8BITDO` and `PROFILE_DS4`.

Not everything in a profile carries the same confidence:

- **Axis mappings are treated as known.** The 8BitDo pad's axis order (`X=0, Y=1, LT=2, RX=3, RY=4, RT=5`) is verified against real hardware in the Linux source project's `docs/findings.md`, and pygame wraps the same SDL backend that verification used. The DS4's axis order (`X=0, Y=1, RX=2, RY=3, LT=4, RT=5`) follows the standard SDL GameController convention for DualShock 4 pads — not independently tested by this project, but reliable enough to build on.
- **`PROFILE_DS4`'s face/shoulder buttons are now verified** against a real DS4 via a Windows diagnostic run (`scripts/windows_diagnostics.py`, 2026-09-23): `SOUTH=0, EAST=1, WEST=2, NORTH=3, TL=9, TR=10`. That same pad reported 0 hats — its D-pad is exposed as extra buttons instead — so `hat_index` stays `None` and D-pad-driven combos aren't wired up yet.
- **`PROFILE_8BITDO`'s buttons/hat are still unverified.** SDL/pygame numbers buttons and hats independently of axes, with no equivalent standard convention to fall back on the way there is for axes — guessing here risks binding the wrong physical button to a macro. It ships with an empty `button_map`, `hat_index=None`, and `button_mapping_verified=False` until someone confirms these against real 8BitDo hardware.

A profile with `button_mapping_verified=False` can still drive the rudder fold, mouse look, and left-stick passthrough (all axis-only) — only combo macros are blocked on the missing button/hat data.

`find_profile(name)` matches a `pygame.Joystick.get_name()` string against known profiles by case-insensitive substring, checking each profile's `name_match` tuple of aliases (`PROFILE_DS4` matches both `"wireless controller"`, the Bluetooth name, and `"ps4 controller"`, the USB name a real DS4 reported on Windows) and returns `None` for anything unrecognized — callers (see `res/device_scan.py`) surface that as a clear "no profile for this controller" message rather than guessing a mapping.

### What `tests/test_profiles.py` covers (14 tests)

- **`TestControllerProfileValidation`** — the dataclass itself: a complete `axis_map` (covering all six required roles) constructs fine; a `axis_map` missing any required role raises `ValueError` at construction time, so an incomplete profile can never silently exist; `button_map`/`hat_index`/`button_mapping_verified` all default to their "nothing verified yet" values.
- **`TestProfile8BitDo`** / **`TestProfileDS4`** — each shipped profile's `axis_map` matches its documented source (the Linux findings table, or the SDL DS4 convention) exactly; `PROFILE_8BITDO`'s button/hat data is still unverified and empty, confirming the honesty constraint above hasn't quietly regressed; `PROFILE_DS4`'s button data matches the real-hardware-verified values above, with `hat_index` still `None`; each profile is present in the `PROFILES` registry.
- **`TestFindProfile`** — case-insensitive substring matching for both profiles' name-alias tuples (including `PROFILE_DS4`'s `"ps4 controller"` alias), a lowercase-name match, an unrelated controller name returning `None`, and an empty string returning `None`.
