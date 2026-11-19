# On-demand Keyence VS popup — 2026-11-08

Branch `feat/vision-camera-on-demand-popup`. Previous work/design preserved. No PLC edits, camera commands/configuration, FTP receiver, image archive, runtime deployment, publication or commit.

## Behavior

The inactive inline iframe in CameraConfiguration is replaced with an Open Interface button. Its native onPressed action opens a dedicated TcHmi.Controls.System.TcHmiPopup (the installed native popup, rather than the uninstalled Beckhoff-namespace popup from the IV example). It does not write any PLC command or camera program.

The modal popup is 1000 x 680 for the 1366 x 768 design, with a Keyence VS - Camera header and Close button. Its registered content hosts a native percentage-sized TcHmiIFrame with Src http://192.168.0.30/. Existing manual trigger, program selection, status LEDs and operation message remain unchanged.

TargetFileHostPreload=False and TargetFileHostKeepAlive=False ensure the camera content is created only when opened and disposed when closed. Installed framework source confirms file-host destruction before onClosed and popup abort on parent detach. Thus opening the VisionTab alone does not load the camera interface; closing the popup or navigating away disposes the viewer. No custom JavaScript was added.

This displays the camera's existing web interface, including its own controls and normal result-view lock/unlock behavior while open. It does not extract an image-only widget or certify that the displayed frame matches a PLC verdict. Closing removes the page context; it does not send a custom camera unlock/reset command or prove server-side lock-release timing. The modal prevents ordinary clicks on background HMI controls; it is not a PLC or TwinSAFE interlock.

## Validation

- check_popup.py verifies native button/open target, lazy content/no keep-alive, native close/detach disposal implementation, content registration, sizing, unique IDs and JSON, plus exact preservation of all other VisionTab controls/bindings.
- Existing manual-camera selection/trigger/LED binding validator passes. Its comparison excludes the newly authorized button/popup area. Earlier inline-frame assertions are historical and superseded by this popup design.
- Native MSBuild HMI compilation passed, exit 0, result saved. No PLC build required for this HMI-only change.
- No live camera image rendering or HMI publication performed; no image file storage added. Normal browser caching is independent of a deliberate captured-image archive.

## Supervised acceptance after authorized publication

1. Enter VisionTab without clicking Open Interface: verify no camera-page connection/polling is created.
2. Open Interface: confirm page/session and camera image fit/readability, native Close/X behavior and existing camera user permissions. Do not use a second web trigger/program selection concurrently with PLC-owned inspection.
3. Close and navigate away: verify the iframe/page is removed and camera network polling stops; confirm result-handshake behavior before starting normal manual/automatic inspection.
4. Repeat open/close and test reconnect, camera unavailable, HTTP/HTTPS/browser LAN permissions, absence of new archive files, and normal PLC first-image/error recovery behavior. Popup lifecycle checks do not establish those physical/runtime properties.
