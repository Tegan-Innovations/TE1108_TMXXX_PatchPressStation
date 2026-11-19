# M1 and real Patch Dispense — 2026-11-05

Branch: `Patch_Feeding_Commissioning`, following checkpoint `108a039`. No runtime download, activation, ADS write, motor move or HMI publication was performed for this increment. Existing unrelated PLC/HMI/user edits were preserved.

## Confirmed process and ownership

The operator clarified that Term19 Input6 is consistent across the patch and does not cross holes. Input5 is stuck TRUE pending bracket repair and is explicitly commented out. Only Input6 participates: after a new dispense request, detect patch TRUE (including initially TRUE), then wait for FALSE after motion has been observed. No initial FALSE is accepted as end-of-patch. Future use of both sensors requires separate seen/falling-edge qualification; uncommenting an expression alone is insufficient.

`FB_PatchFeedManager` remains the sole owner of all three PLCopen axis wrappers. M1 uses negative direction and the existing 30.0 velocity reference, in NC axis units/s (nominal mm/s; actual linear scaling remains a physical commissioning matter). Its controller is prepared in permitted operating modes, but velocity motion requires a station dispense demand. M2/M3 retain their independent sensor policies. Shared faults inhibit feeding. Busy now includes M1, so controlled machine stopping also waits for its motion control to settle.

`FB_PatchDispenseStation` owns optical qualification, tooling sequence, Ready/Busy/Fault and completion result. Existing interface methods and station enums remain; `Update` and the manager `Cyclic` contracts intentionally gained inputs/outputs, and their single machine caller was migrated. The existing main scan order is preserved: the manager consumes the preceding station demand; the station consumes freshly updated axis status. Allow for one PLC scan plus MC/NC response and deceleration after the optical edge. No distance or position move was introduced.

The complete sequence is:

| Step | Action / required feedback |
|---|---|
| 10 | Vertical UP clearance, then raise nest; require extended TRUE/retracted FALSE |
| 20 | Run M1 negatively; wait for Input6 TRUE; enable air immediately on detection |
| 21 | Continue M1 and air; require observed motion and Input6 FALSE |
| 22 | Clear M1 demand; keep air; wait for actual standstill and axis FB not busy |
| 40 | Vertical DOWN; cut air on extended TRUE/retracted FALSE |
| 50 | Hold position through the bistable valve, with both coils off; 5 s release dwell |
| 60 | Vertical UP; require retracted TRUE/extended FALSE |
| 30 | Keep vertical UP and lower nest; require retracted TRUE/extended FALSE before Complete |

Term19 Input9/10 were already linked and mapped as `bMembraneTransferRetracted` / `bMembraneTransferExtended`; these are now the actual vertical feedbacks. Input6 also had an existing raw terminal link; mapping/application input fields were appended to carry it into the station. No I/O/NC links or drive parameters were changed. No configuration activation is needed specifically for this increment; PLC deployment and HMI republication are needed. The sensors must be physically connected and verified before HOME can complete.

## Manual operation and HMI

Dispense Patch is motor-only: steps 20/21/22, with no new nest, vertical stroke or air request. An existing index hold-UP is preserved if required. Its completion never marks a product PASS. Run Sequence executes all steps; automatic requests execute that same complete station sequence. New requests require stable/locked/stationary index, appropriate mode enable, safety/air, no stop/reset/fault and no conflicting manual action. Native `onPressed` writes were added to the two existing buttons and consumed/rearmed in the PLC. Native condition actions now bind Ready/Busy/Fault indicators to the existing `GVL_HMI.stStatus.stPatchDispense` fields. Existing designer layout and controls were retained; no JavaScript added.

Automatic nest result storage and one-time accounting remain in the existing process coordinator. Manual full sequences are commissioning operations; they do not change that coordinator into a manual production-accounting path. No nest identity, persistent data, counter, enum or TwinSAFE ownership was changed. New input/status members were appended; rebuild dependent ADS/type consumers. Old vertical placeholder fields are retained for compatibility, with comments identifying the actual feedbacks.

## Equipment review and recovery

As explicitly requested, UP is continuously commanded while AutoCycle or Manual with Indexer Enable can index, subject to safety/door/air and commissioning. During a sequence the station has exclusive pneumatic ownership, so that background hold cannot override DOWN or release dwell. Opposing coils are mutually excluded. Individual Manual DOWN is blocked with Indexer Enable or an active sequence/index move.

Index movement now additionally requires vertical UP TRUE/DOWN FALSE, station not busy, M1 not busy, and no active vertical command pulse/down output. Thus raised nest or active motor-only dispensing also blocks index. This extends existing permissives; it does not replace TwinSAFE or establish physical safety from software status alone.

Controlled station stop cancels M1/air first, waits for standstill, raises vertical and only then retracts the nest. Manual station disable during an active process requests this controlled recovery. Safety/air loss withdraws commands and invalidates incomplete results; ordinary fault output handling remains de-energised. HOME preserves the existing support-retract pulse/order and now requires real vertical UP feedback instead of a timed claim. M1 feed detection is bounded by 30 s; pneumatic movements use `tStationSupportTimeout` (existing configured timeout). Vertical sensor conflicts, UP loss during feed, DOWN loss during dwell, nest UP loss and motion/feedback timeouts fault the station and clear its process outputs. Generic station event 9 displays the actual station diagnostic; existing per-axis events remain.

These are engineering-reviewed source changes under the requested scope, not physical validation of valve duty, stopping distance, clearance or TwinSAFE. Verify those on the mechanism. Air onset is currently detection-based; a later mid-patch onset remains a commissioning adjustment and has not been guessed.

## Verification

- Fresh PLC Release/x64 build: success, zero failed projects (10:08 UTC). Existing Safety project ADS timeout warning 1861 persists; Error List also contains earlier hardware/NC log messages, separated from compiler diagnostics.
- HMI Release/TwinCAT HMI build: completed successfully, zero failed projects (10:03 UTC), using the exact project path after COM project enumeration failed. No publication or browser rendering performed.
- Saved/live section hashes verified for all 16 edited PLC objects/members; final code readback and scoped whitespace checks performed. Existing degree-glyph encoding in unrelated machine comments was normalized for comparison only.
- `check_sequence.py` executes saved ST branches with scripted sensor/axis/timer feedback. Passed: Input6 initially 0/1, optical qualification, standstill gate, motor-only/no-product-PASS, complete sequence, release timing gate, stop at every step, HOME feedback, sensor loss/conflicts, watchdogs, output arbitration, index-hold conditions, native HMI bindings and server symbol declarations.
- Existing feeding/wrapper tests passed with M1 command ownership updated; M2/M3 start/stop, hysteresis, permission loss, watchdog/reset and controlled stopping remain covered.

These checks are not drive simulation, live ADS verification, HMI rendering or physical commissioning.

## Required supervised commissioning evidence

1. With air/safety/door prerequisites established and machinery clear, verify Input6 patch polarity and Input9 UP/Input10 DOWN physically; ensure no simultaneous end-position signals. Confirm HOME cannot complete with disconnected/missing UP feedback and gives a bounded diagnostic.
2. In Manual, Patch enabled and index locked/stationary: test Dispense Patch with Input6 initially FALSE and TRUE; verify negative M1 motion at the intended speed, actual stopping position/distance, no pneumatic stroke/air, one feed per button press and command rearming.
3. Run Sequence: verify vertical UP before nest UP, complete optical feed, M1 standstill before DOWN, air onset/cutoff, actual 5 s dwell, UP sensor before nest DOWN and Ready/Busy/Fault indications. Record coil/output and sensor traces. Verify already-required UP holding does not interrupt dwell or drive both coils.
4. Repeat the complete cycle in AutoCycle with a known physical nest. Verify index is blocked while M1/tooling is active, permitted only at valid clearance, and result stored once at the correct nest; failed/interrupted cycles must not become PASS. Exercise an empty/disabled nest under existing coordinator rules.
5. Test Stop at motor feed, DOWN, dwell, UP and nest retraction. Verify the described recovery order, no autonomous restart, controlled door-lock retention and index inhibition. Test reset, leaving Manual, Patch disable, reject/cycle-stop request and restart after a fault.
6. Under the site's safety validation procedure, test door opening, air/safety loss, missing/conflicting support/vertical feedback, lost optical signal, M1 error and failed stop/reset. Confirm safe physical response, the right diagnostic, no counter duplication and full initialization before reuse. Existing index unknown-position/two-hand release/re-actuation protections must remain effective.

Do not treat PASS from the branch tests, successful builds or commissioning flags as production sign-off.
