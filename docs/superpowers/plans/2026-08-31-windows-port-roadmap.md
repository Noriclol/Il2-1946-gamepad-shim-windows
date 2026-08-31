# Windows Port Roadmap

Companion to `2026-08-31-portable-logic-core.md`. That plan is fully detailed and executable today with no Windows machine. This document sketches the two remaining plans at design level only — they need real hands-on verification against a Windows machine, IL-2 1946, and physical controllers before a bite-sized TDD plan would be trustworthy, so writing exact code now risks locking in guesses (pygame axis/button *index* numbers especially) that can't be checked yet.

Decisions already settled (from the grill-me session, 2026-08-31) that both plans below must follow:

- **Runtime:** Python, native Windows (no Wine/Proton) — IL-2 1946 runs directly.
- **Input:** `pygame` (SDL2 joystick) for enumeration and reading. Boot-time console picker: lists all currently-connected controllers, remembers the last VID:PID+name choice in a config file, defaults to it but allows override.
- **Controller support:** multiple profiles from day one — 8BitDo Ultimate/Pro 2 and DualShock 4, both mapped onto the logical-role vocabulary from the logic-core plan (`res.logical_input` / `res.combos`). An unprofiled controller shows a clear error, not a guessed mapping.
- **Output:** vJoy for the virtual gamepad (custom DirectInput device — arbitrary axis/button/hat shape, not ViGEmBus's fixed XInput/DS4 layout). `SendInput` via `ctypes` for mouse-look motion and keyboard-macro keystrokes.
- **No physical-pad hiding needed** — vJoy's device persists across sessions before the shim even runs, so IL-2's bindings target it directly and never shift. This eliminates the Linux source project's entire "Later: make the source invisible" problem.
- **Packaging:** one installer (Inno Setup or NSIS) that silently installs the vJoy driver, installs a PyInstaller-frozen `.exe` of the shim, runs `vJoyConf` to configure the device shape, and drops a Start Menu shortcut — zero manual steps for a non-technical end user.

## Plan 2 (sketch): Windows I/O layer

**Goal:** Wire the portable logic core to real hardware and real output — the part that can only be verified on an actual Windows machine.

**New files (design-level, not yet locked):**

- `res/profiles.py` (or `res/profiles/` package) — a `ControllerProfile` dataclass (VID:PID or name-match pattern, axis-index -> role mapping for X/Y/triggers/right-stick, button-index -> logical role mapping, hat-index -> `HAT_X`/`HAT_Y`) plus one instance per supported controller. The 8BitDo profile can start from the already-verified SDL axis table in the Linux source's `docs/findings.md` (axis 0=X, 1=Y, 2=LT, 3=RX, 4=RY, 5=RT; 11 buttons; 1 hat) since `pygame` uses the same SDL backend — but button *index* order is driver-dependent and must be re-verified on Windows, not assumed identical to Linux. The DS4 profile has no prior verified data at all and needs to be built from scratch against real hardware.
- `res/device_scan.py` — `pygame.joystick` enumeration, the console picker (list + remembered-choice prompt), and a `matched_profile(joystick) -> ControllerProfile | None` lookup with a clear error path for no match.
- `res/vjoy_output.py` — wraps `pyvjoy` to drive the gamepad: rudder axis + passthrough axes/buttons/hat, mirroring what the Linux source's `build_gamepad_uinput`/`build_rudder_uinput` did for evdev/uinput. Needs the vJoy device #1 shape decided (axis count, button count = max across all shipped profiles' logical roles, POV hat) and documented as a `vJoyConf` invocation, not created programmatically at runtime (vJoy devices are configured once, ahead of time).
- `res/sendinput_output.py` — `ctypes` bindings for `SendInput`: relative mouse motion (drives the logic core's `RelAccumulator`/`MouseLookState` at a fixed-rate loop, replacing the Linux source's `mouse_tick_loop`) and keyboard tap events (glyph string -> virtual-key code table, replacing the Linux source's `emit_tap`/`build_keyboard_uinput`).
- `res/config.py` — persists the remembered controller choice (VID:PID + name) to a small file (e.g. `%APPDATA%\IL2Shim\config.json`).
- `res/main.py` — entry point wiring: pick a device, build vJoy + SendInput outputs, run the pygame event loop, dispatch through `ComboDetector`/`fold_rudder`/`stick_to_velocity` from the logic core, same shape as the Linux source's `res/main.py`.

**Needs verifying on real Windows hardware before any of the above is trustworthy:**

- Exact `pygame` axis/button/hat index numbers for the 8BitDo pad and the DS4 (do NOT assume they match the Linux evdev/SDL indices — re-run `pygame.joystick` enumeration on Windows and record real values, the same way the Linux source's `docs/findings.md` was built from direct observation).
- Whether `pyvjoy` + the vJoy driver actually install and drive a device correctly on the target Windows version (community-signed driver — may need test-signing mode enabled).
- Whether IL-2 1946 natively binds to a vJoy DirectInput device the same way it bound to the Linux source's evdev/uinput gamepad — repeat the HOTAS CONTROL binding verification from the Linux source's `docs/operations.md`.
- Whether the DirectInput instance-registry caching behavior described in the Linux source's `docs/problem.md` (§DirectInput's own instance registry) also affects native Windows DirectInput the same way it affected Wine's emulation of it — unconfirmed, worth a quick registry check (`HKCU\...\DirectInput\VID_xxxx&PID_yyyy\Calibration`) once a Windows machine is available, since it could still matter even without Wine in the picture.
- `SendInput` behavior under whatever anti-cheat or focus-stealing-prevention IL-2 1946 (or Windows itself) applies to games — confirm keystrokes/mouse motion actually reach the game window while it's focused.
- The glyph->keystroke table in `res/sendinput_output.py` needs an explicit choice between VK-code SendInput (layout-aware, ambiguous for Swedish-specific glyphs) and scancode SendInput (layout-independent, needs a US-physical-position table) — it must account for the Swedish (`se`) layout assumption inherited from the Linux source. The three Nordic glyphs' known physical-key mapping (Å/Ä/Ö -> KEY_LEFTBRACE/KEY_APOSTROPHE/KEY_SEMICOLON) plus the punctuation glyphs (`,`/`.`/`-`) is recorded in `res/combos.py`'s module docstring.

## Plan 3 (sketch): Installer / packaging

**Goal:** One installer a non-technical end user runs once, after which the shim starts from a Start Menu shortcut with no further setup.

**Pieces (design-level):**

- PyInstaller `.spec` freezing `res/main.py` and its dependencies (`pygame`, `pyvjoy`) into a single `.exe` — removes the Python/venv/pip step for the end user entirely.
- Inno Setup (or NSIS) script that: bundles and silently runs the vJoy driver installer; installs the frozen `.exe` to Program Files; runs `vJoyConf` non-interactively to configure device #1's shape (decided in Plan 2); creates a Start Menu shortcut.
- Admin-rights handling: driver installation needs elevation — the Inno Setup script requests it for the installer itself so the end user isn't prompted mid-setup beyond the one UAC dialog.

**Needs verifying before this plan can be written in detail:**

- Actual silent-install command-line flags for whichever vJoy driver build gets used (varies by vJoy version/fork).
- Whether the target Windows version accepts the vJoy driver's signature as-is, or needs test-signing mode enabled first — if the latter, the installer needs to either walk the user through that one-time step or the project needs to pick a driver build that's still properly signed.
- End-to-end test: fresh Windows VM or the friend's actual machine, run the installer, confirm the shortcut launches the shim with zero manual steps.

## Suggested order

1. Execute the logic-core plan now (no blockers).
2. Get any Windows machine — doesn't need to be the friend's, doesn't need IL-2 installed yet — and spend a short session just running `pygame.joystick` enumeration against both controllers to replace the guessed profile data with verified index numbers. This unblocks writing Plan 2 in full bite-sized detail.
3. Write and execute Plan 2 in full, verifying against IL-2 1946 itself at the end (HOTAS CONTROL binding to the vJoy device).
4. Write and execute Plan 3 once Plan 2's device shape and dependency list are final — packaging what already works end-to-end, not packaging speculatively.
