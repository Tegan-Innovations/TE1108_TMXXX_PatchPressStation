# Commissioning software checkpoint — 2026-11-05

Branch: `Patch_Feeding_Commissioning`; preceding checkpoint: `108a039`.

The operator requested this Git checkpoint while the machine is undergoing mechanical modifications and is unavailable for physical testing. This is an **offline-validated software milestone, pending physical commissioning**. No download, runtime write, configuration activation, equipment movement, HMI publication or safety deployment was performed as part of recording this milestone.

Included behavior:

- M1 negative feed at the existing 30-unit/s reference, qualified by patch detection on Term19 Input6; temporary exclusion of Input5 while its bracket is repaired.
- Complete Patch Dispense sequence, motor-only Manual dispense, native HMI commands and Ready/Busy/Fault indication.
- Explicit temporary timed Patch vertical mode (1 s travel reference) until Input9/10 are wired. Its message identifies estimated rather than measured position; restoring feedback mode and physical verification remain required.
- Vision 0/180 endpoint qualification at 1 s, intermediate 90 marker latch, initial 100 ms post-marker photo delay, duplicate-pulse rejection and preserved camera handshake/evaluation-error recovery.
- Shared automatic/HOME/Manual endpoint interpretation and explicit rejection of a missing reference or late capture window.
- The already-used `ST_VisionResults.nPBUBMagnetOK` field: its existing camera assignments preceded this checkpoint, but its DUT declaration was missing from the preceding Git tree. Including it is necessary for a reproducible build; it does not introduce a new evaluation rule.

Physical status: earlier M3 Manual operation was reported working. The M1/full Patch sequence, temporary vertical assumptions, new rotary qualifications, final exposure angle, fault/recovery scenarios and resulting production behavior are not accepted as physically validated. The 100 ms value does not guarantee a 115-degree exposure; intermediate raw-0 pulses must be shorter than the endpoint qualification interval and reliably observable by the 10 ms PLC task.

Validation evidence: successful offline PLC build, successful HMI build after adding Patch bindings, saved/live source checks, and source-driven tests for feeding, Patch sequence, both vertical modes, rotary marker/window behavior and all four camera programs' 10130/40008 recovery. The existing Safety-project ADS timeout warning 1861 remains separate from compiler success. No claim of rendered HMI or live ADS/physical verification is made.

Detailed behavior, limitations and supervised acceptance cases:

- [M1 / Patch Dispense](patch-dispense-m1/HANDOVER.md)
- [Temporary vertical mode](patch-vertical-timed/HANDOVER.md)
- [Vision rotary marker](vision-rotary-marker/HANDOVER.md)

Reproducible source checks, run from repository root:

```text
python engineering/patch-feeding/implementation/check_logic.py
python engineering/patch-dispense-m1/check_sequence.py
python engineering/patch-vertical-timed/check_timed.py
python engineering/vision-rotary-marker/check_marker.py
python engineering/vision-rotary-marker/check_camera_regression.py
```

The shared camera regression helper and scenarios are self-contained against the current saved PLC methods; historical snapshot JSON is not required. Generated XAE caches, local publication settings, historical diagnostic captures and unrelated user edits are excluded from this checkpoint. Source IO/NC link and hardware-parameter trees were checked unchanged against `108a039`; no new configuration activation requirement is introduced by these source changes. The reviewed PLC/HMI changes still require their corresponding deployment before later physical tests.
