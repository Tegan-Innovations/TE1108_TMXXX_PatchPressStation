# Vision manual camera controls — 2026-11-08

Branch `feat/vision-manual-camera-controls`. Existing designer edits and unrelated development work preserved. No commit, download, activation, ADS write, live camera trigger or HMI publication.

## Implemented

- Native ComboBox retains its designer position and ID. Selecione is index 0/no selection; Imagem 1..4 are indices 1..4, translated in PLC to camera programs 0..3. Selection is explicit; opening the tab cannot issue a trigger. Selection changes load the requested camera program using the existing RequestChangeProgram.
- Camera Trigger uses native onPressed -> one command BOOL, consumed every PLC scan. Ready enables the button only after the requested program is reported, camera Run, PROFINET connection and Trigger Ready are present, with no camera fault, ACK, pending result or manual operation. Busy selections/clicks cannot restart or change an active capture.
- Manual camera control requires machine Manual, Vision Manual Enable and existing motion-safety status. It relinquishes ownership on Stop/reset/mode loss, station processing, manual sequence or HOME request. It does not command mechanical movement or change any safety/interlock behavior.
- The existing single FB_VSCamera instance remains the only camera output owner. Its RequestTrigger/Cyclic/GetResults/RequestResultsAck handshake is reused. Manual results go to a separate private payload, never nVisionResults or nest statistics. Automatic program-1 rotation gating remains within the automatic branch. Existing automatic request/copy/ACK order is preserved.
- Capture selection is latched until completion. A ten-second budget covers program confirmation, trigger ACK, result and result/ACK withdrawal. Connection/Run/error loss or timeout cancels the request; no automatic retrigger. Existing camera errors are not silently cleared to permit another test.
- Pass/Fail clear at a new request, selection change or loss of manual ownership. They latch only from the selected program's captured inspection-completed/passed flags. Invalid verdicts cannot become PASS. Capture count is diagnostic only and does not count production.
- Native LED actions use the existing green/grey colors; Fail uses red. Connected is separate from Run: EL6633 operational, linked PnIoBoxState=0 and PnIoBoxDiag=2 (AR established/no other diagnostics). New WORD inputs initialize invalid (FFFF). Ready is the stricter capture permissive above; Busy is the pending manual operation/program load. Pass/Fail are the last manual capture verdict.
- Two read-only offline links were added to vs-01 Inputs/PnIoBoxState and Inputs/PnIoBoxDiag. All prior process/NC/FSoE links are preserved. GVL structures and named interfaces remain unchanged; new GVL symbols/private members are added.

## Image remains dependent on camera source

The original placeholder Textblock was replaced by a native TcHmiImage in its rectangle, with a small operation-message row below it. Its Src is deliberately empty: no validated image endpoint or transfer path was available in the project. The mapped camera data contains results/status bytes, not pixels. A question requesting camera IP and a working browser/image URL is pending. No fabricated snapshot endpoint, stream, authentication or captured image is supplied.

Once a supported image URL/transfer is identified, bind/refresh the native image source against completed captures and validate that it represents the same capture/program, including caching and image timestamp/identity. A live viewer alone does not prove display of the inspected frame. If the camera exposes only a remote application, confirm embedding and read-only behavior before substituting an IFrame. IP alone does not establish an image API.

## Validation evidence

- Four PLC object snapshots, expected-hash previews and writes. Saved source matches intended sections (check_saved.py/saved-hashes.json).
- PLC offline build succeeded, failedProjectCount 0, no compiler diagnostics, before creation of the two validated configuration links; PLC source was unchanged afterward. Full structured result retained.
- Link endpoints both verified WORD/16-bit. Mapping comparison verifies exactly two additional read-only input links and preservation of all earlier links.
- The attached Visual Studio solution stopped responding later, so its HMI COM build guard refused to proceed. A native MSBuild HMI build then completed with exit 0 using the installed engineering directory explicitly. This is build evidence, not designer rendering or publication.
- check_manual.py executes saved manual-control ST with mocked protocol responses: all four selections, loading, selection latch, PASS/FAIL, repeated click rejection, mode/sequence/HOME/stop/reset/safety exclusions and connection/error/timeout cancellation.
- check_camera_protocol.py executes actual current FB_VSCamera ST for programs 0..3 with PASS/FAIL, one-scan results before/after ACK, retained payload, read/ACK and rearm. Timers/OCR/date remain mocks. The older check_handshake.py fails because its old initial-state fixture lacks bResetRequest; the current test supplies default-zero reset/recovery fields without changing production camera code.
- check_hmi.py validates native bindings, actions, all new ADS members/access, exact preservation of unrelated designer content and mapping changes. Ten added HMI symbols are verified separately from the existing 251-symbol IO validator.
- Existing IO/HMI validator passes after refreshing only its GVL readback and accounting for the two approved connection links. No existing terminal/state/process/safety link checks were removed.
- Task-scoped diff has a whitespace finding in a blank line of the user's pre-existing VisionTab design; unrelated layout was preserved.

## Supervised acceptance after authorized deployment

With Manual and Vision Manual Enable, normal safety conditions and no active station sequence/HOME: confirm opening the tab does not trigger; choose each image and verify camera-reported program before Ready. Press once and capture trigger/ACK/result/ACK-withdrawal timing, fresh verdict and diagnostic capture count. Repeated clicks/held button must not duplicate captures. Test load delay, camera not Run, PN disconnect, stale pending result, timeout and invalid/ambiguous verdict under an approved test method. Verify stop/reset/mode loss and subsequent new click recover without unintended trigger. Manual tests must not alter nest results/counts.

Then verify normal automatic four-program inspection, rotation capture rules, product verdicts and statistics remain correct after manual use. Validate actual connection diagnostics during disconnect/reconnect. Image acceptance is outstanding until a real source and frame identity are established. Record HMI rendering/live ADS verification separately from these offline tests.
