# Vision Manual Ready/Busy indication

Implemented offline on fix/vision-manual-ready-busy. User withdrew the preceding
rotation/horizontal interlock request; this change is limited to Manual status
publication and the native Ready LED subscription. No interlock changes were made.

The machine previously replaced Manual Ready with an enable/availability test
without checking HOME, while Busy remained derived from the Vision FB's separate
state. Individual manual outputs are owned by the machine, so the two indications
could disagree. The saved Ready LED also subscribed to a mixed dot/colon symbol
path instead of the exact registered ADS name used by its comparison action.

The Manual publication block now recomputes Busy from NOT current bHome OR active
manual sequence OR active manual HOME. Ready requires bHome AND NOT Busy, plus
the existing manual permission, manual enable and no-station-fault conditions.
Thus an enabled, healthy station at HOME is Ready/NOT Busy; leaving HOME makes it
NOT Ready/Busy; returning HOME restores Ready when no commanded sequence remains
active. A sequence still at HOME is Busy, preventing Ready during initial camera
acquisition. Disabled/faulted states do not falsely advertise availability.

The HOME field is refreshed by fbVision.Update before this block. The resulting
status is then copied to stStatus.stVision and published by PRG_HmiStatus. The
internal fbVision.IsBusy(), controlled-stop behavior, retained Initialising
indication override and non-Manual state handling were preserved.

The HMI remains native: the Ready event now uses
ADS.PLC1.GVL_HMI.stStatus.stVision.bReady, matching the existing registered mapping
and native condition comparison. Busy uses its existing correct mapping.

Validation: expected-hash dry-run/write/readback succeeded. Saved section hashes
match verified-signature.json. check_status.py executes all 256 Manual input
combinations, 2048 non-Manual cases and HOME/depart/return transitions; verifies
the native bindings and byte-for-byte preservation outside the Manual block
after reconciling the known MCP degree-glyph transport encoding artifact.
Saved Vision station tests and overall IO checks for 251 symbols passed. PLC
Release/x64 and HMI Release offline builds succeeded with zero failed projects;
the remaining Error List entries were field logs, not new compiler diagnostics.
Scoped whitespace checks passed.

No activation, download, runtime writes, equipment movement, HMI publication or
commit performed. Existing unrelated workspace changes were preserved.

Supervised acceptance after approved PLC/HMI deployment: enable Vision in Manual
with actual tooling HOME, observe Ready on/Busy off; execute an already-approved
manual movement to leave HOME, observe Ready off/Busy on; return via the approved
HOME procedure and observe Ready on/Busy off. Check sequence/HOME active while
physically at HOME, fault/disabled indications, mode transitions, page reopening
and ADS reconnection. Actual designer/browser rendering and live deployed status
have not been verified by this offline change.
