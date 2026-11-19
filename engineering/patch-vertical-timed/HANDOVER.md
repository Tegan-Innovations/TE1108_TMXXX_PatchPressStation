# Temporary Patch vertical timing — 2026-11-05

The operator explicitly requested temporary exclusion of the unwired vertical feedbacks (Term19 Input9/10). In the current fault-number assignment, N32/Station3 is the generic Patch Dispense fault (event slot 9); N5/Station0 is initialization timeout (slot 5). Waiting for unwired UP can produce the station timeout followed by failed initialization. This is source-based causality; the actual runtime diagnostic was not read, so other causes remain possible.

## Explicit temporary mode

`GVL_Motion.stPatchFeedSettings.bUsePatchVerticalFeedback` defaults **FALSE**. `tPatchVerticalMoveTime` defaults **T#1S**, using the previous commissioning travel-time reference. Raw Input9/10 and their mappings remain unchanged; no input, safety bit or physical feedback is forced TRUE. Effective process readiness is selected explicitly between real feedback and a private timed position estimate. Inputs are ignored only for the requested vertical component in temporary mode.

The station tracks previous-scan final published UP/DOWN outputs, after machine fault/output overrides. Separate TONs estimate completion only after a continuous command of the configured duration. Reversal invalidates the opposite estimate. Safety/air loss, commissioning disable, component fault, reset, HOME and initialization invalidate estimates. No elapsed command means no new position confirmation. DOWN estimation persists through the existing bistable release dwell; dwell remains 5 s. HOME, complete dispensing and controlled-stop recovery use this explicit mode rather than waiting on disconnected inputs.

Index and nest raising require extra care because UP can drift without pressure: in timed mode, an old UP estimate alone does **not** permit index or nest raising. They require the ongoing UP command to have completed its travel time. The index permissive also requires the current UP output, valid support sensors, no station/M1 busy condition and existing safety/index conditions. UP holding remains active while an index already in motion completes during controlled Stopping or a Manual index-enable change. Sequence ownership still prevents hold-UP from overriding DOWN/dwell. A private timed estimate is not evidence of physical clearance and cannot detect jammed tooling, a failed valve or wrong travel time.

Full sequence preparation can raise UP by time before raising the nest. Motor-only dispensing retains its no-new-pneumatic-command behavior, using the last timed position for its start prerequisite; index is separately blocked without current timed hold-UP. Other station support, drive, optical, stop and timeout checks remain active. N32/N5 themselves were not suppressed. A persistent non-fault message, `Patch vertical: TEMP timed mode`, identifies the temporary mode using existing HMI events. No HMI source, I/O link, NC parameter or TwinSAFE configuration was changed in this increment.

## Restoring feedback

After connecting and physically verifying Input9=UP/retracted and Input10=DOWN/extended, set the source default `bUsePatchVerticalFeedback := TRUE`, rebuild/deploy, and perform initialization and fault tests. The real-feedback path restores sensor-based position/conflict/loss checks and index readiness. The timed estimate is discarded in that mode. Settings are non-retained; an online TRUE alone does not change the FALSE source default for future initialization.

## Verification and deployment boundary

- Fresh PLC Release/x64 build succeeded at 10:37 UTC, zero failed projects. Existing Safety project ADS timeout warning 1861 remains separate from compiler success.
- Saved/live hash comparisons passed for all ten changed objects/members; scoped whitespace checks passed.
- Saved-ST branch tests passed for both real-feedback and timed paths: disconnected inputs, mandatory timed HOME, raw inputs unchanged, full feed/down/dwell/up/nest sequence, current hold-UP for index, safety/command-conflict invalidation, restored physical sensor checks and controlled-stop hold-UP. Existing M1/M2/M3 logic tests also passed.
- No download, configuration activation, ADS write, equipment movement, HMI publication performed. This increment needs PLC deployment; it creates no new I/O links and no HMI publication requirement.

Under competent commissioning supervision, first confirm actual full UP/DOWN travel is shorter than the selected 1 s with margin, and verify physical clearance while UP is held. Test HOME with both inputs unwired, full and motor-only dispense, automatic/manual index inhibition before travel time, Stop during an index and at each process step, air/door/safety loss, reset/reinitialization and opposite-coil exclusion. Verify existing support feedback conflicts/timeouts and M1 faults still alarm. Then, after wiring, repeat with feedback mode TRUE, missing signals and conflicting signals. Builds and scripted feedback do not establish physical safety or production release.
