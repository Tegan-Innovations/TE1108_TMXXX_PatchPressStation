# Patch vertical physical feedback — 2026-11-07

Branch: `feat/patch-vertical-real-feedback`. Existing unrelated changes preserved. No commit, download, activation, runtime write, motion command or HMI publication.

## Change

Existing mapping verified: Term19 EL1809 Input9 -> bMembraneTransferRetracted -> station UP; Input10 -> bMembraneTransferExtended -> station DOWN. ReadInputs and the sole station Update caller already propagate these physical values correctly.

ST_PatchFeedSettings now defaults bUsePatchVerticalFeedback to TRUE. PRG_StationProcessSettings explicitly assigns TRUE before PRG_Main each scan, ensuring an existing FALSE in RAM cannot retain the commissioning timer mode after an online change. The public settings layout and legacy timed implementation remain compatible, but current machine execution always selects physical feedback.

Existing station checks now use actual UP/DOWN for HOME, dispense and index readiness. Both active is a conflict; neither active cannot certify a position. Existing travel timeouts, loss-of-feedback faults, drive standstill, stop/reset/air/door/safety behavior and M1 dual optical / 20 mm/s changes are preserved.

Manual PatchVerticalUp and PatchVerticalDown LEDs use native Beckhoff trigger/condition/color actions cloned from the existing support LED. Their event and condition expressions subscribe to the already registered read-only Term19 channels 9/10. They display raw sensor states independently, so a conflict remains visible. No JavaScript added. All manual command markup is unchanged.

## Validation

- Concurrency-protected snapshots, preview and writes of two PLC sections; XAE readback saved.
- PLC offline build successful, failedProjectCount 0; HMI offline build successful, FailedProjects 0. Existing field events in Error List are separate from compilation.
- check_sensors.py executes actual saved station ST: four physical sensor combinations, HOME awaiting UP, descent awaiting DOWN, loss of DOWN during dwell, completed commissioning timers cannot certify position, physical feedback selected before machine execution.
- Existing full dispense/feed-only/stop/reset-related feedback/HOME and actuator arbitration tests passed; process settings tests passed; IO/HMI validator passed with 251 symbols.
- Saved LED event/condition bindings and existing server symbols checked; exact comparison confirms manual commands and unrelated markup preserved. No live ADS or rendered designer test performed.

## Supervised equipment acceptance after authorized deployment

With safe tooling clearance, stable/locked table and normal safety/door/air conditions: confirm UP gives Input9/Up LED only, DOWN gives Input10/Down LED only, and travel gives neither. HOME must wait for UP; dispense must wait for DOWN before release dwell, then UP before nest return/index. Verify the expected sensor timeout/conflict/loss fault behavior using an approved test method, plus controlled stop, safety withdrawal and reset with no unintended restart. Capture inputs, LEDs, station steps, outputs and index permissive as evidence. Physical timing and process quality remain to be validated.
