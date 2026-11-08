# M1 manual LEDs — 2026-11-07

Branch `feat/patch-m1-manual-leds`. Only PatchTab.content product source changed; server configuration is byte-for-byte preserved from the task baseline. Existing unrelated changes retained. No PLC changes or runtime writes.

- PatchMotorMotorReady: green when AxisDriveMotor.bEnabled AND NOT bError AND NOT bMoving; grey otherwise.
- PatchMotorDispensing: green when AxisDriveMotor.bMoving; grey otherwise. Movement takes precedence over Ready, including controlled deceleration. A moving axis with an error still displays movement.
- Source FB_PatchFeedAxis.Cyclic publishes bEnabled from MC_Power.Status / monitor-mode operational status, bError from its fault latch or NC ErrorStop, and bMoving from NC discrete/continuous motion or stopping. These existing read-only ADS mappings were verified.
- Native conditions and color actions match the existing LEDs. Both controls reevaluate on attachment and on each of the three status changes. No JavaScript, motion command or interlock changes.

Offline validation: check_leds.py passed all 8 status combinations for both controls and all four event handlers; exact green/grey colors, subscriptions/conditions, read-only symbols and preservation of other controls/configuration verified. Existing IO/HMI validator passed (251 symbols). Scoped diff whitespace check passed.

HMI build was attempted, but the connected Visual Studio instance no longer exposed the open solution; the solution guard stopped the build. No successful new build is claimed. No designer rendering, publication or live ADS validation performed.

After authorized HMI publication, verify enabled/stopped/no-error -> Ready green only; movement/deceleration -> Dispensing green only; stopped disabled or faulted -> both grey; opening the tab during movement initializes correctly. Confirm no stale color when enabling, disabling or resetting faults. Offline state combinations cannot establish live update timing.
