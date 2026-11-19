# EL6910 controller diagnostics

Implemented on `feat/el6910-controller-diagnostics`. This page shows internal
TwinSAFE controller diagnostics; it does not repeat terminal channel states.

## Source and acquisition

The installed Beckhoff EL69xx ESI matching EL6910 revision `#x00150000` exposes
CoE read-only objects F100 (logic state/cycle counter), F188/F18C (FB state/diag),
F190/F191 (connection state/diag), F192/F193 (group state/diag) and 10F3 (history).
Thus `mapState/mapDiag` need not be enabled in the Safety project. The earlier
discussion that Safety diagnostic exports were necessary is superseded by this
confirmed CoE path.

Added installed `Tc2_EtherCAT 3.7.1.0`, verified before use. The new standard PLC
FB_EL6910Diagnostics is called once from PRG_HmiStatus, after terminal status
updates. It publishes GVL_EL6910Diagnostics.stStatus. It is not consumed by any
machine permissive, process sequence or TwinSAFE decision. Existing MAIN scan
order, persistent data and public existing DUT layouts are unchanged.

Master NetId `172.18.239.27.2.1` and fixed slave address `1003` were confirmed from
XAE engineering metadata, not guessed from the terminal number. Review these
constants when moving the project to a different EtherCAT configuration.

The reader executes one SDO upload at a time, with a 50 ms inter-request gap and
1 s request timeout. There are 75 jobs per sweep, so this is a slowly refreshed
maintenance display, not a real-time trace. Only the terminal being OP enables
polling. Disabled OP, unsuccessful/short replies and a 30 s stalled sweep discard
current values instead of displaying a default zero as a valid diagnosis.
Unsupported objects are explicitly unavailable. No write/acknowledgment/reset,
CompleteAccess history read, startup command or safety export is added.

## Page

Main_IOs still loads T03_EL6910. Its native content has the existing EtherCAT LED,
the correct EL6910 image, logic state/cycle counter and group slot 1 summary.
The EtherCAT LED still means state exactly 8, separately from safety logic RUN.
Native buttons change a Region between three read-only Datagrids:

- Connection slots 1..6, state and diagnostic codes in hex.
- FB slots 1..24, matching the current project block count, with raw state/diag.
- The latest eight stored diagnostic records, newest first, severity, raw device
  timestamp, decoded English description and raw code/Text ID/parameters.

Slot numbers are deliberately labelled as CoE slots. They are not asserted to be
the Safety alias ConnectionId, physical terminal number or editor block order.
Confirm their correspondence against TwinCAT online diagnostics before attaching
physical names. A raw zero is not independently interpreted as safe/healthy.
Group state and group diagnostic descriptions follow the Beckhoff tables; unknown
values retain their numeric value. Block/connection codes are not interpreted as
universal error enums. The history supplies the more specific explanation.

History text is generated from all 592 English Text IDs in the installed matching
ESI. Integer `%d`/hex `%x` parameters are bounds-checked and substituted; unsupported
parameter encodings remain visibly unresolved with raw parameter bytes. Unknown
Text IDs keep numeric identity. Degree signs are written as ASCII `deg` to avoid
the observed XAE/source encoding discrepancy. Malformed/empty records do not
reuse previous decoded fields.

The history capacity/newest pointer are read, eight ring entries are copied to a
staging buffer, and the newest pointer is checked again before publication. A
changed pointer rejects the sweep. The snapshot is best-effort: a full ring wrap
between the two pointer reads cannot be ruled out. History is historical, not an
active alarm list. Timestamps remain explicit Local/DC hexadecimal device values;
no unverified calendar conversion is claimed. Raw details can be horizontally
scrolled in the history grid. No JavaScript or external polling service is used.

## Verification

- Offline PLC Release/x64 and HMI Release builds succeeded, zero failed projects.
- The Error List retains a dated 2026-11-06 EL6910 `0x3410` restart message; it is
  historical runtime logging, not a new compiler error. No error list was cleared.
- Nine objects were read back through MCP; final-readback.json matches saved source.
- check_bindings.py verifies the generated objects, all nine HMI mappings, array
  schemas, noneditable columns, native-only navigation and read-only acquisition.
- st_function_test.py executes the saved ST functions with protocol fixtures,
  signed/hex parameters, unknown IDs, timestamps, truncation, empty records and
  1,000 deterministic malformed frames. It is a bounded offline interpreter, not
  the TwinCAT runtime or a hardware simulator.
- test_reader.py executes the saved scheduling ST with mocked SDO replies: single
  flight, ring wrap, OP loss during a request/final request, sweep expiry, short
  replies, unavailable objects and changed-history rejection.
- Existing check_io.py was extended for the three nested contents and passes for
  251 actual typed symbols. Existing process/NC/FSoE links remain preserved.
- No TwinSAFE source/configuration changes, activation, runtime access, ADS writes,
  download, publication or new commit were performed for this task.

## Supervised acceptance, before relying on the page

1. Deploy the standard PLC/HMI through the approved procedure. This feature adds
   no I/O mappings and requires no new Safety download. The earlier IO milestone
   has its own activation requirements; those are not cancelled by this change.
2. With equipment stopped and the deployed version identified, open Term3 and all
   three tabs. Verify actual browser/designer rendering, grid scrolling and that
   no value is editable. Verify the new ADS symbols and permissions after login.
3. Compare logic state, group slot, all displayed connection/FB slots and history
   records against XAE/CoE. Confirm firmware object availability, slot numbering,
   newest-pointer/capacity interpretation, Text IDs and raw timestamp basis.
4. Observe existing authorized stop/run/error/recovery scenarios, without inducing
   a safety fault solely for this display. Confirm group diagnostics identify the
   corresponding history. Do not equate EtherCAT OP or logic RUN to machine release.
5. Under an approved communication test, verify OP/ADS loss and reconnection remove
   misleading old values and recover polling. An unsupported object must remain
   unavailable. Check mailbox traffic and safety timing under representative load.
6. Compare history with enough existing records to exercise wrap/order. Confirm
   unknown firmware messages remain readable by raw IDs and are not mistranslated.

References: [Beckhoff EL6910 manual](https://download.beckhoff.com/download/Document/automation/twinsafe/el6910_en.pdf),
[CoE SDO read FB](https://infosys.beckhoff.com/content/1033/tcplclib_tc2_ethercat/56996235.html).
Installed ESI hash, full Text ID dictionary and the exact job plan are retained in
esi-evidence.json. No physical or live ADS verification is claimed.
