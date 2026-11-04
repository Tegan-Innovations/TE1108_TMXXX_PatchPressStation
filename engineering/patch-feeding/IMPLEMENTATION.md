# Patch feeding — offline implementation, 2026-11-04

Branch: `Patch_Feeding_Commissioning`. No activation, download, runtime writes or motor moves were performed for this implementation. This checkpoint includes motor control sources, NC links and saved commissioned drive configuration; operator-authorized HMI improvements are included; local publication profile and generated caches are excluded.

## Architecture and ownership

`FB_IndexedPatchPressMachine.Cyclic` calls one `FB_PatchFeedManager`. The manager composes three independent `FB_PatchFeedAxis` objects, each owning its PLCopen Power, MoveVelocity, Halt and Reset instances. `Tc2_MC2, 3.3.72.0` was added from the installed library repository. Axis status is refreshed once per scan. Monitor-only axes do not continuously invoke Power/Move/Halt, preserving commissioning ownership.

| Motor / terminal / NC ID | NC name | GVL_Motion record | Reference velocity |
|---|---|---|---|
| M1 / 15 / 1 | M1_DriveMotor | AxisDriveMotor | 30 mm/s |
| M2 / 16 / 2 | M2_PatchFeedRollMotor | AxisPatchFeedRollMotor | 10 mm/s |
| M3 / 17 / 3 | M3_WasteRollMotor | AxisWasteRollMotor | 50 mm/s |

M1 remains monitor-only until its sensor policy is specified. M2 now uses its own sensor latch as described below. M3 uses velocity motion because the defined stop condition is sensor feedback, rather than a measured relative distance. Each complete `Axis.NcToPlc` structure is linked to NC Outputs/ToPlc and each `Axis.PlcToNc` to NC Inputs/FromPlc: six links total. Saved mapping comparison found exactly these six additions and no removed/changed links. NC IDs, axis parameters and IO configuration match the pre-implementation snapshot; only NC names changed.

The previous GVL records AxisReelPayout, AxisMaterialIndex and AxisSlack were intentionally replaced by the explicit names above. External ADS consumers using previous names must migrate. `ST_Axis` layout was preserved. Inspect `GVL_Motion.AxisWasteRollMotor.lrActPosition`, `.lrActVelocity`, `.bError`, `.udiErrorId`, and `.Axis.NcToPlc` for full NC feedback; equivalent records exist for M1/M2. Application alarm entries are station 3 slots 31–33 for axis errors and 34 for manager supervision. Reset is operator-requested, asynchronous and bounded; reset-pending suppresses immediate reassertion while commanding no motion. Failed reset restores the fault.

## M3 policy and commissioning guard

Start demand: Term19 Input11 OR Input15. Retain demand through intermediate sensor positions. Stop demand when Input11 and Input15 are both FALSE and Input12 OR Input16 is TRUE. Loss of permission clears demand. Permission requires AutoCycle or Manual with Patch Station Enabled, commissioned station, motion safety, closed door, safe air and no stop/fault/cycle-stop request.

`GVL_Motion.stPatchFeedSettings.bWasteRollConfigured` now defaults TRUE after the operator confirmed negative M3 direction. `eWasteRollDirection` defaults MC_Negative_Direction. Travel is sensor-controlled, so no distance target depends on physical scaling; scaling still determines actual speed and stopping distance. These settings are not retained. This enables automatic M3 commands after deployment when the existing operating permissives and sensor demand are present. The three reference speeds are configured as requested; acceleration/deceleration/jerk zero use commissioned NC defaults. Power/stop watchdogs are 5 s; the provisional rocker-run watchdog is 30 s. Negative direction was confirmed by the operator; actual speed, stopping response, dynamics and maximum safe travel/time remain physical commissioning checks. No parameters from Drive Manager commissioning were overwritten.

Controlled stopping waits for feeding to finish decelerating and retains the door-lock request while feeding is busy. The door FB also receives feeding-not-busy as its process-safe input; this does not verify other tooling. Fault/safety withdrawal removes software motion permission; TwinSAFE remains the safety authority. No TwinSAFE logic was edited.

## Evidence and required physical checks

Fresh offline build completed successfully, zero failed projects. The Error List also contains earlier hardware/NC messages, including M2 following error 0x4550, and a Safety-project ADS timeout warning 1861; these are not new PLC compiler errors. Saved/live comparison passed for all ten changed objects/members. Scoped diff whitespace checks passed. `implementation/check_logic.py` executes saved ST branches against scripted PLCopen feedback: power/start/halt ownership, held execute, immutable active command, permission loss, safety withdrawal, missing links, NC faults, watchdogs, sensor hysteresis and asynchronous reset all passed. These checks do not simulate drive dynamics or establish machine safety.

Under competent commissioning supervision, after reviewing motion parameters and confirming stopping response:

| Preconditions/action | Required result/evidence |
|---|---|
| Activate configuration for renamed axes and six NC links; download reviewed PLC | Three NC IDs and complete feedback visible; M1 receives no automatic commands; M2 uses Input14/Input13 |
| Guard FALSE; any sensor demand | No automatic M3 enable/move |
| Guard confirmed TRUE; Manual enabled; safe prerequisites; either down sensor | M3 starts in correct direction at verified 50 mm/s |
| Both down FALSE, neither up TRUE; then either up TRUE | Demand remains through gap, then controlled deceleration to standstill |
| Manual disabled, Stop, or controlled cycle stop during motion | Demand clears; no immediate restart while Halt active; door remains requested locked until feeding stops |
| AutoCycle with station permitted | Same sensor policy; no dependence on dispense-sequence step |
| Door opening, air loss, safety loss or axis fault | Permission withdrawn; verified safe physical response; correct alarm/cause; no autonomous fault reset |
| Operator Reset with a recoverable axis fault; also failed reset | No motion during reset; clears after valid completion, or bounded reset-failure indication |
| Missing up feedback / power not ready / stop not completing | Correct bounded watchdog fault; no unbounded command |
| Stop/reset/restart and PLC restart | No stale demand resumes; configuration defaults return TRUE / negative direction after initialization; other stations/index interlocks remain valid |

Record actual direction, speed measurement, stopping distance/time, sensor sequence and alarm/reset evidence before production release. I/O/NC link changes require **Activate Configuration**; PLC download alone does not apply them. Generic existing event presentation is reused; no HMI publication was introduced by this feature.


## M2 implementation ? 2026-11-04

The operator reported successful M3 operation in Manual; alarms and other modes remain physically untested. M2 is now commanded positively with reference velocity 10 mm/s (NC length units/s; physical scaling remains an equipment commissioning matter). Term19 Input14 starts a retained demand; Input13 stops it with priority even if Input14 is also TRUE. Input14 does not need to remain active during travel. This is level-sensitive, matching M3: an active Input14 can request movement when operating permission returns, unless Input13 is active.

Existing mapping is reused: Input14 -> bBottomRockerUp -> new manager bPatchFeedStart; Input13 -> bBottomRockerDown -> bPatchFeedStop. No I/O/NC links or drive parameters changed in this increment. The only manager caller was updated. Existing MC wrapper, shared operating/safety/stop/reset gates and M2 NC error event 32 are reused. M2 operates independently of M3 demand/configuration; common faults inhibit feeding. Controlled stopping/door retention now uses M2 OR M3 busy.

New non-retained setting `tPatchFeedRollRunTimeout` defaults to provisional 30 s; watchdog fault 1103 identifies M2 failing to reach Input13. New `stPatchFeedStatus.bPatchFeedRollDemand` is appended to the nonpersistent status contract; rebuild consumers. Existing field offsets are preserved. M2 velocity default changed from 15 to 10. No HMI bindings, persistent structures or AXIS_REF links changed.

Fresh offline build: success, zero failed projects (15:41 UTC); preexisting Safety ADS timeout warning 1861 remains. Saved/live readback passed for all five changed objects/members. Branch-execution checks cover M2 latch across sensor gap, Input13 priority, simultaneous independent M3 demand, permission/safety withdrawal, timeout/cause retention/reset and combined busy status. Physical validation and downloads were not performed.

Required supervised checks: in Manual with Patch Station Enabled and safe prerequisites, activate Input14 and confirm positive M2 motion at the intended speed; clear Input14 and verify continued travel; activate Input13 and verify controlled stop. Test both inputs TRUE (no M2 motion), M2/M3 independent and simultaneous operation, station disable, Stop, Reset, door/air/safety loss, AutoCycle and missing Input13/axis-error recovery. Verify the door remains requested locked during controlled deceleration of either motor and record actual stopping response. Input14 still TRUE after Input13 clears permits a new move; confirm this matches the mechanism. Existing stop/reset/fault tests for M3 remain outstanding. This increment requires rebuilt PLC deployment; no new configuration activation is required specifically for these M2 source changes.

M2 direction correction: operator corrected the required direction to positive. Only the M2 MC direction argument changed; M3 remains negative. Speed and sensor rules are unchanged.

End-of-day checkpoint: includes operator HMI changes, PatchDispense.png and project inclusion. HMI source XML/JSON and credential-difference checks passed; designer rendering, a new HMI build and live binding checks were not performed in this checkpoint. M1 remains monitor-only and is the next implementation task. Alarm and full recovery commissioning remain pending.
