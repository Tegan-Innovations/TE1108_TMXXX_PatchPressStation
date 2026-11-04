# Vision Station — partial commissioning handover, 2026-11-04

The operator considers Vision Station partially fulfilled. Further process/quality decisions remain pending discussion with the customer.

Implemented: trigger acknowledgment and captured-result latch for four inspections; persistent program-change requests; per-piece result reset; nominal +500 ms delay for the rotating image; camera RUN indication and automatic-cycle interlock; bounded recovery of identified 10130/40008 capture errors as product FAIL; per-image error diagnostics; resettable Warning presentation with short image-only text. Warnings preserve the product FAIL and use the existing HMI Alert icon. A failed camera recovery remains an equipment fault.

Two PROFINET UDINT links were added from the camera Assignable Status Error0/Error1 Code to GVL_EtherCAT.udiVisionError0Code/udiVisionError1Code. The operator confirmed that codes initially stayed zero in the PLC despite appearing in I/O; applying the configuration resolved the transfer and recovery then worked with messages. Whenever I/O-to-PLC links are changed, explicitly remind the operator to activate/apply the configuration and verify online transfer; a PLC-only update must not be assumed to apply a new I/O mapping.

Offline build and bounded source/model tests passed for recovery, delayed numeric error codes, short result pulses, retained FAIL, Reset/Stop withdrawal, unknown/pre-existing errors, warning acknowledgment/rearm and automatic RUN gating. Two added links were compared against all prior links; non-PLC/safety/axis configuration was unchanged by that mapping task. Warning rendering/reset behavior after its latest change still requires equipment verification. Local engineering evidence remains in the shared checkout. No production/process-quality sign-off is implied.

Pending: client decision on inconclusive versus conservative FAIL/manual inspection; rotating-picture repeatability; mechanical PBUP/nest alignment and pickup reliability; OCR/date byte-layout verification; independent diagnosis of first Reset from Stopped entering Fault. No automatic recapture of images 1/2 was introduced. Physical recovery timing and actual defects remain commissioning matters.

Only reviewed camera/event source, the two camera-code I/O links, and this handover belong to the checkpoint. Other pre-existing HMI edits, XAE generated metadata and local engineering artifacts remain outside it.
