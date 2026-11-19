# Patch and Vision process Settings — 2026-11-05

Implemented offline on Patch_Feeding_Commissioning, after checkpoint 713b2c9. No new commit/push, runtime connection, ADS writes, activation, download, publication or physical commissioning performed for this task.

## Operator interface

Replaced the legacy reservoir content in settings_PatchDispense.content and populated the supplied settings_VisionStation.content. Both use native Beckhoff NumericInput, Textblock and Button controls with saved ADS bindings/actions, no JavaScript. Added Vision Station to the existing Settings tree and included its content in the HMI project.

Each row shows Edit, Applied, units and an allowed range. Apply awaits native writes of each current numeric control Value before writing its PLC request. Cancel restores the edit buffer from applied values. PLC consumes command BOOLs every scan; repeated clicks do not require page reload. Apply and numeric edits are disabled by the PLC availability status while running/saving; PLC also rejects direct requests in those conditions. Administrator/Engineer can edit/apply, Operator and ordinary system users have read access, Guests have none for these new symbols. No existing group permission was changed.

| Station | Setting | Default | Allowed |
|---|---|---|---|
| Patch | M1 Drive Motor speed | 30 mm/s | 0.1–30 mm/s |
| Patch | M2 Patch Feed Roll speed | 10 mm/s | 0.1–10 mm/s |
| Patch | M3 Waste Roll speed | 50 mm/s | 0.1–50 mm/s |
| Patch | Release dwell after vertical DOWN | 5000 ms | 100–15000 ms |
| Patch | Airblow delay from first patch detection | 0 ms | 0–2000 ms |
| Vision | Moving-photo delay after first accepted 90° marker | 100 ms | 0–1000 ms |
| Vision | Continuous 0°/180° endpoint confirmation | 1000 ms | 1000–3000 ms |

These ranges are initial software limits, not evidence of physically validated process windows. Direction, NC dynamics, safety/protection thresholds, movement/camera watchdogs, temporary vertical-feedback bypass and optical-sensor workaround remain outside these settings. Existing temporary modes are unchanged. Vision confirmation uses the existing common endpoint qualification for HOME, Manual and Auto; its minimum remains 1 s. The unused legacy tRotate180Hold is not exposed. The photo delay does not establish a precise pneumatic angle; if the capture window closes, existing failure handling remains active.

Airblow delay starts on first Input6 detection and stays timed through feed/standstill/descent. Air turns off when DOWN is confirmed, even if a long configured delay never elapsed before that point. Feed-only never requests air or the vertical cylinder. Release dwell begins in the existing DOWN dwell state. Defaults retain the prior process timing.

## PLC ownership, contracts and persistence

New ST_PatchProcessSettings and PRG_StationProcessSettings; populated the previously empty ST_CameraProcessSettings. Appended typed edit/applied buffers and command/status globals to GVL_HMI and two setting records to the end of GVL_Persistent. Appended fields change ADS layouts: rebuild clients using offsets; new HMI leaf mappings and type definitions are included. Existing persistent variables and nest/history data were not reset or reordered. Preserve persistent data during deployment and verify the newly appended defaults against the actual runtime's migration outcome.

PRG_StationProcessSettings runs immediately before PRG_Main, after the existing Heat Stake process-settings adapter. It accepts Apply only in Stopped/ReadyToStart with process station busy flags clear, feeding/drive busy clear and all motor Moving flags false. Manual, Auto, Initialising, Fault and stopping requests are rejected and consumed. Cancel wins over Apply. Entire structures are range-checked before acceptance, including non-finite speed rejection via positive bound checks. Invalid retained records load typed defaults with an explicit review/Apply message at startup.

Accepted values become applied RAM settings and initiate FB_WritePersistentData using the project's existing local-port 851 convention. Saving, successful completion, error flag/code and retry messages are exposed. A failed save explicitly says values were applied but not saved; Apply can retry. New requests during a save are rejected rather than queued. The two stations share this writer and can be saved together if both requests arrive in one scan. Existing independent persistence writers retain their existing behaviour.

The application adapter copies only the three speeds into GVL_Motion.stPatchFeedSettings. Patch/Vision Update methods now accept their typed process settings and retain them internally; the sole active callers in FB_IndexedPatchPressMachine were updated. I_ProcessEquipment.Cyclic signatures remain unchanged. No I/O links or NC configuration were changed.

## Evidence

- PLC offline Release build succeeded with zero failed projects; separate final diagnostics query reported zero errors/warnings.
- HMI Release build succeeded after final Apply actions, zero failed projects.
- verify_saved.py: all 13 affected PLC sections match final XAE readback (line-ending/legacy degree-glyph normalisation only).
- check_settings.py executes saved transaction ST with scripted writer feedback: every machine state and busy gate, every parameter limit, NaN, atomic reject, Cancel priority, command rearm, save busy/success/error/retry, restart hydration and invalid retained defaults. Also validates exact native bindings, sequential Apply writes, mapping destinations, permissions, navigation, project inclusion and scan order.
- check_process_timing.py executes saved Patch branches with timer models: zero/nonzero air delays, detection, feed standstill, DOWN air-off, minimum/default/maximum dwell, feed-only isolation. Existing full dispense, HOME, stop/fault/output arbitration regressions also pass.
- Existing check_marker.py, check_camera_regression.py, check_timed.py and operator-two-parts/check_two_parts.py pass after adapting test timer fixtures to the new zero-delay air timer and milliseconds input conversion. No machine results are inferred from these scripted tests.
- Scoped git diff --check passed. Unrelated designer/source/generated changes remain in the workspace. Source/build checks do not verify designer rendering, live ADS or browser operation.

## Required supervised commissioning

1. With the machine in Stopped and tooling safe, log in as Engineer. Open both Settings entries; verify layout, all Edit/Applied values, units and role permissions. Confirm Operator cannot write. Check current runtime defaults, especially new persistent entries, before any movement.
2. Edit a final field and immediately Apply; verify that field reaches Applied, Saving then Applied and saved. Cancel another edit and verify no applied change. Repeat Apply, navigate away/back and verify commands rearm. Restart through the approved procedure and verify retained settings/edit hydration.
3. During Auto/Manual/Initialising and while any feed motor or station is busy, verify Apply is unavailable/rejected with no queued change. Test both pages and simultaneous requests. Exercise a controlled persistence failure in an approved test environment: applied values remain explicit, error ID appears, retry succeeds. Never induce storage faults on production equipment solely for this check.
4. With safe mechanical clearance and approved motion supervision, validate M1 negative/M2 positive/M3 negative directions unchanged, speeds in actual NC units, sensor-based start/stop and existing motor alarms. Commission a safe operating range within the software bounds; maximum values preserve the prior commissioned speeds.
5. Full Patch sequence: validate zero and selected airblow delay, DOWN air-off, actual release dwell, vertical UP and nest DOWN before indexing. Feed-only must remain motor-only. Repeat stop/reset, safety/air/door loss and feedback-conflict/loss checks with the existing procedure. Current timed vertical commissioning mode remains temporary.
6. Vision: confirm 0°/180° qualification at 1 s and a selected longer value in HOME/Manual/Auto. The transient 90° pulse must not qualify HOME. Verify first-marker delay, duplicate-pulse latch, outbound-only photo, missing/late marker, closed capture window, camera not RUN and inspection error recovery. Check good/bad image results and no duplicate trigger. Repeat stop/reset and recovery checks.

Deployment requires PLC update and HMI publication. No Activate Configuration requirement was introduced because no hardware link changed; if a later change modifies I/O links, remind the operator to Activate Configuration. Mechanical timing, real browser bindings, persistence across a real restart and production acceptance remain untested.
