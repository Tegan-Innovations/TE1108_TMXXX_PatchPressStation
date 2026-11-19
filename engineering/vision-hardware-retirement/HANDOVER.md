# Vision: removed nest support and intermediate vertical stop

Implemented offline on `feat/vision-remove-support-intermediate`. The operator
confirmed that former intermediate descents at process steps 70 and 140 must
reach the actual DOWN sensor. No runtime writes, download, activation, HMI
publication, equipment movement or commit was performed for this change.

## Final behavior

- The Vision nest support and intermediate-stop sensors no longer participate in
  initialization, HOME, Ready, manual permissions, processing, controlled stop,
  recovery, index permission or fault supervision.
- Process steps 70/140 command vertical DOWN and complete only with DOWN TRUE and
  UP FALSE. Release step 150 additionally requires that same endpoint condition
  before requesting gripper OPEN or completing release. Movement timeout and
  retained sensor-conflict supervision remain active.
- Support-only processing steps 20/90/130 retain their step numbers, now checking
  the existing pick, flip-clearance and replace tooling conditions. Camera steps
  10/100/110/180, marker timing, acquisition, verdict aggregation and nest result
  ownership were preserved.
- HOME follows UP -> rotate 0 -> grip OPEN -> horizontal BACK -> verify HOME.
  Removed actuator-only HOME steps 20/50 are skipped. Reset still invalidates
  incomplete results; Stop enters the existing controlled HOME path.
- Horizontal and automatic rotation requests still require exclusive vertical
  UP feedback. Opposing retained outputs and contradictory retained sensors
  retain their existing interlocks. Door, air, two-hand and TwinSAFE behavior
  were not changed.
- The machine index tooling criterion retains station 1/2 support DOWN TRUE and
  UP FALSE, plus its existing Patch clearance/axis conditions. Vision support
  feedback is no longer part of that criterion. Other coordinator/index/safety
  checks remain present.
- Manual vertical has only UP/DOWN targets. DOWN is available at either known,
  exclusive horizontal endpoint; neither/both horizontal sensors does not grant
  a new DOWN permission. Existing mode/safety/manual-enable checks remain.
- Deprecated public DUT/method/ADS fields remain for compatibility. Their old
  commands are discarded, retired statuses remain FALSE and support fault status
  is None. No fake TRUE feedback was introduced. Existing enum values, public
  signatures, persistent layouts and scan order were preserved.

## Physical boundary and HMI

The obsolete input mappings are inactive in application data. Their raw EL1809
channels remain available only as raw diagnostics and are labelled retired:
Term8 channels 5/6 and 11/12. Four obsolete outputs are always FALSE at station,
machine, application and final coil-mapping boundaries: Festo module2 coils6/7
(nest support) and module3 coils4/5 (intermediate stop). I/O links and TwinSAFE
files were not changed. Removed channels are not reassigned to other actuators.

The native Vision manual page no longer contains Support Nest, Intermediate
command or the inferred intermediate indication. UP/DOWN controls, physical
feedback bindings and command rearming are retained. The IO diagnostic cards
mark the four input/four output channels as retired/spare.

Vision support alarm slots 6/7/8 retain their classification/numbering but have
no active condition, preserving later alarm IDs. Existing latched alarms may
need the normal operator Reset after deployment; no automatic reset was added.
Actual Vision tooling/camera faults continue through the generic Vision event.

## Validation

- All 15 edited sections were previewed, written with expected hashes and read
  back from XAE. Saved-source SHA-256 matches the authoritative readback hashes.
  The MCP text payload adds an encoding layer to existing degree glyphs; the
  checker explicitly reconciles that transport artifact against the matching
  hashes without rewriting unrelated temperature/banner text.
- Final offline PLC Release/x64 and HMI Release builds succeeded with zero failed
  projects. The XAE Error List still contains field logs for drive PD-Watchdog,
  EL6910 restart and repeated Festo CoE emergencies. These entries have no PLC
  source locations and were reviewed separately from compiler success. Their
  physical causes were not investigated or corrected in this task.
- `test_station.py` executes saved Vision ST with scripted sensor/timer feedback:
  all 16 removed-input combinations, real DOWN gating at 70/140/150, HOME routing,
  retained conflicts/timeouts, controlled Stop, safety loss, Reset and UP clearance.
- `test_proposals.py` executes the reviewed machine expressions, checks remaining
  station supports, manual horizontal endpoint permissions, retired physical
  coils and preserved alarm classifications. `check_saved.py` verifies those
  reviewed sections match the saved/XAE implementation and actual HMI bindings.
- Marker and four-program camera recovery regressions passed. Existing overall
  IO verification passed for 251 typed symbols. Scoped whitespace checks passed.

These are offline checks, not a physical simulation, live ADS verification of the
new software or acceptance of the new mechanical travel.

## Required supervised acceptance

| Preconditions/action | Required result/evidence |
|---|---|
| Equipment isolated/clear; new hardware arrangement reviewed | Confirm full DOWN clearance at both horizontal endpoints, gripper geometry, valve behavior and actual sensor polarity before movement. |
| Approved standard PLC/HMI deployment; identify exact versions | Four retired coils remain OFF in every mode. Old HMI/client requests cannot energize them. No new I/O-link activation or Safety download is introduced by this change. |
| HOME/Initialising with removed inputs low, high and contradictory in an approved test environment | Removed inputs have no effect. Actual UP, horizontal BACK, grip OPEN and qualified rotation 0 remain required; retained feedback loss/conflict faults as expected. |
| Manual UP/DOWN at allowed horizontal endpoints | One action per command; correct endpoint stops the command; no Intermediate/Support UI; no opposing coils. Leaving Manual, disable and safety/air loss cancel appropriately. |
| Full sequence, especially 70/140/150 | Actual DOWN TRUE/UP FALSE is required. No open-gripper request at step150 while DOWN is absent. Verify physical pick/replace, stop distance and full-stroke collision clearance. |
| Stop/Reset/fault during descents, grip, flip and camera wait | Existing controlled HOME or fault path, no spontaneous restart/late image, no incomplete product marked PASS and no duplicate counts. |
| Index/automatic operation and remaining station supports | Only the retired support dependency disappears. Remaining supports, Patch clearance, index locking/position, two-hand release/re-actuation and safety remain effective. |
| Known good/bad parts through all nests | Four camera inspections, physical nest identity, fail/not-tested propagation and one-time accounting remain correct. |

Do not treat successful compilation as mechanical clearance or safety validation.
