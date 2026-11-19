# Terminal link repair — 2026-11-19

Seven links restored through native XAE Automation Interface, with endpoint type/size checks and readback from both the open XAE mapping and the saved tsproj:

- Term 21 EL3314-0092, TC channels 1–4 Value -> GVL_EtherCAT.stTerm21_EL3314.iEL3314_Ch1–4 (DINT, 32 bits).
- Term 20 EL4022, InfoData State -> GVL_EtherCAT.stTerm20_EL4022.stTerminalInfo.nTerminal_State (UINT, 16 bits).
- Term 21 EL3314-0092, InfoData State -> GVL_EtherCAT.stTerm21_EL3314.stTerminalInfo.nTerminal_State (UINT, 16 bits).
- Term 22 EL6633, InfoData State -> GVL_EtherCAT.stTerm22_EL6633.stTerminalInfo.nTerminal_State (UINT, 16 bits).

The existing two EL4022 analog output links and camera PROFINET payload/control/diagnostic links were preserved. Legacy iEL4028_Ch1/2 member names remain compatible with the existing ST_EL4022 type.

The missing EL6633 state feeds PRG_HmiStatus terminal-operational decoding, which is required by bCameraConnected. The machine uses Connected to gate new manual preparation and camera transport readiness. This is a source/configuration finding, not confirmation of the running machine state or the exact N24 event.

The XAE tree already contained only Devices 1 and 2 before this repair. Saving the project also persisted that pre-existing unsaved removal of disabled Device 3 (EtherCAT Automation Protocol). This repair did not call DeleteChild or modify that device. The baseline file still contained it; the final file diff shows its removal in addition to the seven new links.

Evidence: before.tsproj, mapping-before.xml, mapping-after.xml, links.json, status-before.txt and diff-before.txt. Git diff --check for the tsproj passed. No PLC source, safety logic, scaling or thresholds changed. No build, runtime read/write, activation, download, manual trigger or physical movement was performed.

## Git handover scope

The handover commit includes the pre-existing hardware scan/configuration changes in the tsproj, the terminal renames in GVL_EtherCAT and their PLC callers, the new ST_EL4022 type and its project inclusion, plus the seven restored links. These source adaptations were required dependencies already present locally before the link repair. Other local brake, motion, HMI and process edits are excluded; mixed files are staged with only the terminal-name changes. The saved tsproj also includes the existing PROFINET configuration edits and the previously pending removal of disabled Device 3 described above; review these against the equipment before activation. Staging did not modify working source files.

Only HANDOVER.md, links.json and repair.ps1 from this evidence directory are included in the handover commit. The baseline project and full before/after captures remain local evidence. The repair script is an audit of the applied procedure; it rejects already linked endpoints and is not intended to run again on the repaired checkout. No compilation or equipment test is claimed for the handover commit.

## Required equipment verification after separately authorized activation

With equipment secured and competent supervision, confirm the physical order is 20 EL4022, 21 EL3314-0092, 22 EL6633. Confirm all three terminal states indicate OP and the temperature channels are plausible against independent/reference readings before enabling heat. Verify pressure output response against the installed regulator and measurement without changing scaling incidentally.

Confirm PROFINET state=0, diagnosis=2, terminal-operational=true and Connected=true. Confirm camera RUN and clean handshake. With normal manual safety, door, air, index, product and tooling prerequisites satisfied, select Vision Manual Enable again if RUN loss withdrew it; prepare the intended image and verify the expected position, then trigger and verify one accepted capture/result and proper rearming. Record exact active-event text, including N24, if any block remains. Do not force any permissive. Physical timing, process quality and safety behavior remain unverified.
