# TODO

- **Verify D-pad direction button indices on real hardware.** `PROFILE_DS4.dpad_button_map` (`res/profiles.py`) has `DOWN`=16, `LEFT`=17, `RIGHT`=18 as a guessed sequential continuation of the one verified index (`UP`=15, confirmed 2026-09-23 via `scripts/windows_diagnostics.py`). Until DOWN/LEFT/RIGHT are confirmed the same way, the 16 D-pad-direction chorded combos (`TABLE_1`/`TABLE_2` in `res/combos.py`) may fire off the wrong physical direction. `dpad_mapping_verified` stays `False` until this is done.

- **Reconfigure vJoyConf's device #1 to 32 buttons.** Generic raw button passthrough (`res.vjoy_output.GENERIC_BUTTON_OFFSET`) now forwards every pygame button index the pad has with no named role, at `pygame_index + 10`. A vJoyConf setup from before this change (6 buttons) will silently drop any button beyond the original 6 named roles. Testers need to re-open vJoyConf and bump device #1 to at least 32 buttons (leave device #2 as-is: single axis, no buttons).
