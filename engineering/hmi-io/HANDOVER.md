# Patch Press HMI I/O — 2026-11-06

Prepared offline on Patch_Feeding_Commissioning. No activation, download, runtime writes, TwinSAFE deployment, publication or machine test. No commit made for this task.

## Final interface

Main_IOs.content retains its existing TreeView and central Region. Selecting a terminal loads that terminal's content. No overview dashboard was added. Digital pages follow the supplied T04_EL1918 structure: a full-size native UserControlHost using the existing 4/8/16-channel card UserControls, image, terminal-state description and operational LED. All available channels are included, with unassigned channels named CHxx spare. Terminal numbers/models match Devices, including the two distinct devices both named Term21 (EL4028 and EL6633); hardware names were preserved.

The native analog card's numeric value fields are disabled NumericInputs with three decimal places. ChannelCount hides nonexistent channels on 2/4-channel cards; it does not hide real spare channels. Raw terminal values are displayed without inventing engineering scaling. Scaled-value fields remain available in the shared UserControl but are hidden on these pages where no validated scaled binding was supplied. The three drive pages use the same analog-card layout to show the existing NC position, velocity and torque fields, explicitly labelled NC feedback rather than physical analog channels.

Festo valve modules 2/3/4 have eight-channel pages showing the actual mapped output command bits, with their actuator names from PRG_TerminalMapping. LEDs indicate commanded bits, not pneumatic position confirmation. All process-channel values come from existing mapped symbols. No output forcing or process command was added. Active legacy Silicone names and invalid GVL_IO.dw_* bindings were removed from these terminal pages; unrelated unused legacy contents remain untouched.

## Existing terminal diagnostics

Each device uses its own existing ST_Terminal_Info and embedded fbTerminalInfo. PRG_HmiStatus now calls all 23 applicable instances cyclically, publishing sTerminalInfo and bTerminalOperational from nTerminal_State. Operational is TRUE only for exactly 8; combined/error states remain FALSE. The existing FB_TerminalInfo gained a default text for unknown values so an old OPERATIONAL description cannot remain after a transition to an unknown state.

GVL_EtherCAT gained only the missing stTerm12_EL9410 : ST_EL9410, stTerm14_EL9576 : ST_EL9576, and a shared stFestoTerminalInfo : ST_Terminal_Info for the manifold. Existing types were reused. There is no separate diagnostics GVL in the final project. The passive EL9011 end terminal has no process values or EtherCAT state and is identified accordingly.

Six state links already existed. Added 17 read-only InfoData.State links, giving 23 device states in total. Original process, NC and FSoE mappings were checked against the initial full mapping set and remain unchanged. No standard PLC logic or safety decisions consume these diagnostic fields. Native mapping API reference: [Beckhoff variable mappings](https://infosys.beckhoff.com/content/1033/tc3_automationinterface/21842639883.html).

## EL2904 limitation

Individual safe-output feedback for Term6 and Term18 is not exported to the standard PLC. Both alias-device files have MapOutputs=false. The HMI therefore displays all four named rows, with feedback not exported, and hides their channel LEDs instead of presenting default FALSE as measured output state. Their EtherCAT operational LEDs work normally. Names were read from existing TwinSafeGroup1.sal usages: Term6 EnableAir/ResetAir/EnableAir/MainDoorLocked; Term18 MotorsSTOEnabled channels 1–3 and CH04 spare. No TwinSAFE file or FSoE link was modified. Exporting individual safe-output feedback requires a separate reviewed safety task.

EL1918 inputs already have their individual raw FSoE input bits linked to the PLC and are displayed through those existing links. These raw bits do not replace the application's validated TwinSAFE statuses. The earlier preliminary statement that EL1918 channels had no links was corrected after reviewing the complete mapping inventory.

## Validation evidence

- PLC Release offline build succeeded, zero failed projects; final diagnostics reviewed separately.
- HMI Release offline build succeeded after the final card/navigation changes.
- check_io.py verifies all original process/NC/FSoE links, exactly 17 added diagnostic links, 23 total state bindings, all 197 typed PLC/HMI symbols and exact ADS mapping destinations, all channel rows/spares, unique active content IDs, native card interfaces, image-file existence, no physical write actions, disabled analog NumericInputs with three decimals, and cyclic diagnostic calls.
- Saved FB_TerminalInfo statements are executed against ordinary, unknown and combined UINT states: only 8 is operational; unknown values replace stale text.
- Three modified PLC sections were read back from XAE and recorded in verified-sections.json. Source/build checks do not establish browser rendering or live ADS operation. Existing unrelated work was preserved.

## Deployment and supervised checks

Activate Configuration is required because I/O-to-PLC links changed. Update the PLC and republish the HMI using the approved commissioning procedure. No activation/download/publication was performed here.

On the actual browser, verify every tree item loads the correct terminal, both Term21 models are distinguishable, all assigned and spare channels appear, LEDs match physical bits, analog NumericInputs are disabled and show three decimals, and numeric values match XAE/NC. Verify the crossed Heater2/Heater1 EL2502 channel assignment, Vision rotary input15/16 assignment, provisional PBUP Term19 Input1, temporary optical sensor bracket condition and still-pending vertical-sensor wiring against physical installation. Reading those raw signals must not change the existing commissioning workarounds.

Verify terminal transitions 8 -> non-8 -> 8 update both LED and text. Disconnect/reconnect ADS only through the approved test procedure and verify communication errors are visible rather than mistaken for valid channel states. All diagnostic pages must remain read-only in every machine mode. Test EL2904 labels/absence of false LEDs; do not interpret the EtherCAT operational indicator as safety output energisation.

Correct terminal images can be added manually for EL3314, EL4028 and EL6633; no incorrect substitute image is supplied for these models. Festo module images are also left for site documentation. The passive EL9011 needs no process-channel graphic. Validate designer layout and real browser rendering when equipment access returns.

Only check_io.py is intended for repeated validation. Preparation/import/cleanup scripts and backups record this offline session and must not be replayed blindly.
