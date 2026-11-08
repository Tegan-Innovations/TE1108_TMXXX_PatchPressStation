# Dual optical patch feed / M1 20 mm/s — 2026-11-07

Branch: `feat/patch-dual-optical-m1-20mm`. Previous uncommitted work preserved.

## Implemented behavior

- Restore right optical mapping: Term19 EL1809 Input5 -> physical input -> machine input -> station Update. Left remains Input6. New BOOLs appended to the two input DUTs; existing fields retain order. The sole named station Update caller supplies the added input. Persistent setting layouts are unchanged.
- In feed steps 20/21, latch independent detection for each optical input. Either first detection starts the existing air delay; M1 continues until both inputs have detected the current patch, both are currently clear, and actual motor movement was observed. Signals need not overlap. Clear latches on new full/feed-only requests, HOME, initialise, reset, stop, disable and safety loss.
- Keep the existing 30 s feed timeout, motor fault supervision, standstill/busy check before vertical movement, pneumatic order, feed-only result rules and all existing protection/interlocks.
- M1 default and HMI/PLC accepted maximum are now 20 mm/s (minimum 0.1). Existing retained values above 20 are reduced to 20 at settings initialization; lower valid values remain. Other retained fields remain unchanged unless the pre-existing invalid-settings fallback applies. Migration does not trigger a persistent write: review Applied and use Apply while stopped to save. M2/M3 speeds, directions and NC dynamics/protection parameters are unchanged.

## Evidence

15 section snapshots, concurrency-protected previews/writes and XAE readback; saved sections checked against intended text. PLC build successful, failedProjectCount 0; HMI offline build successful, FailedProjects 0. The Error List contains earlier field logs, including M1 following error 0x4550 (and M2); these are not compiler diagnostics or proof of torque deficiency.

`check_dual.py`: actual saved station ST with simultaneous, staggered/reversed and initially-present optical inputs; each input stuck ON/OFF; no observed movement; stop/disable/safety withdrawal; full dispense, feed-only, standstill, dwell, HOME, retained feedback faults and actuator arbitration.

`check_settings.py`: saved initialization and Apply branches, retained M1 migration without changing other settings, out-of-range rejection, stop/save/cancel gates, native HMI limits and saved bindings.

Existing timed-vertical regression and IO/HMI validator passed (251 mapped symbols). Task-scoped diff whitespace check passed. Full repository whitespace check still reports pre-existing whitespace in FB_PatchFeedAxis and earlier test runners.

## Required supervised equipment validation

No runtime write, motion command, download, activation or HMI publication was performed. Offline checks do not validate physical stopping distance or process quality.

1. With machine stopped, after authorized deployment verify right/left polarity and wiring Input5/Input6, and Applied M1 <=20. Review settings and Apply to persist.
2. With stable/locked index, tooling clearance, safety/door/air permissives satisfied: feed-only then full dispense; capture both input transitions, actual velocity, stop demand, actual standstill and patch final position. Accept only if each detects and clears, M1 stops at the intended point and vertical motion begins after standstill. Feed-only must produce no pneumatic action/product PASS.
3. Under an approved test method, confirm either missing/stuck optical input causes bounded feed fault and no vertical descent. Check reset/new request never inherits prior detections.
4. Confirm controlled stop, safety withdrawal, drive fault and recovery retain existing output behavior; no auto restart after reset. Review M1 following error and actual tracking at 20 mm/s separately before production acceptance.
