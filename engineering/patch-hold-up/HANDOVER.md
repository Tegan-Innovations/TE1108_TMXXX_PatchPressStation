# Sustained Patch UP / M2 5 mm/s — 2026-11-07

Branch `fix/patch-hold-up-m2-5mm`. Prior work preserved; no commit or deployment.

## Behavior

AutoCycle already continuously holds UP outside station-owned processing. Manual now also holds UP when Patch Manual Enable is selected and either physical UP or the previous final UP command establishes the raised position. The previous final command retains UP even if its sensor drops. An explicit manual UP pulse establishes the same sustained hold. Manual DOWN has priority and clears the hold through the final output feedback; releasing DOWN does not automatically lift a manually lowered cylinder. Existing index-enabled hold remains intact.

Full dispense, HOME and stop recovery retain station ownership, so the new idle hold cannot interrupt DOWN/release dwell or impose an opposite coil. Manual motor-only feed now receives the hold-UP requirement when Patch Manual Enable is selected (it already requires vertical UP to start). Safety, closed door, safe air and commissioning gates remain unchanged; opening/removing them clears the output. No air/door/two-hand/interlock or NC protection modifications.

M2 defaults and accepted maximum reduced from 10 to 5 mm/s, including both native HMI NumericInputs and range text. Existing retained M2 speeds above 5 are capped on settings initialization; lower valid values and all other process values remain. Review Applied and Apply while stopped to save persistently. No automatic persistent write was added. M1 remains 20 mm/s and M3 unchanged.

## Evidence

Four edited PLC sections obtained via snapshots, previewed and written with concurrency hashes, then read back and checked against saved source. PLC build succeeded (failedProjectCount 0); HMI build succeeded (FailedProjects 0). No download, activation, runtime writes, motion commands or HMI publication.

check_behavior.py executes saved arbitration and settings ST: 2000 scans of Manual/Auto hold, feedback disappearance while holding, manual DOWN priority, UP rearm, safety/door/air/commissioning withdrawal, exclusive processing ownership, M2 retained migration and Apply range. Existing full dispense/feed-only/stop/HOME/feedback/coil arbitration tests, M1 LED state combinations and IO/HMI validator (251 symbols) passed. check_saved.py verifies exact source/readback hashes and native M2 HMI limits.

The older patch-vertical-sensors/check_sensors.py reaches its historical exact whole-PatchTab comparison and fails there because the subsequent authorized M1 LED feature changed that tab; its executable sensor tests pass before that historical fixture check. This is not a sensor logic regression. No historical fixture overwritten.

## Required supervised validation

After authorized deployment, verify sustained Festo UP output and physical clearance in Manual enabled/UP and AutoCycle idle, including idle time longer than the prior gravity drift interval. Verify manual DOWN remains exclusive, then UP reestablishes continuous hold; full dispense DOWN/dwell/UP and feed-only preserve expected outputs. Verify safety withdrawal/door/air loss and reset/recovery retain existing behavior, with no unintended restart. Check actual M2 speed at 5 mm/s and tracking under load; validate following-error behavior without changing protection limits. Capture input states, final coil commands, actual axis velocity and fault history. Offline tests do not validate pneumatic load holding or torque adequacy.
