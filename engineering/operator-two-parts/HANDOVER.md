# Operator product + PBUP presence — 2026-11-05

Implemented on Patch_Feeding_Commissioning. No runtime connection, download, activation, ADS writes or physical commissioning performed for this change. No commit made.

## Behaviour and interface

In AutoCycle a new index accepts both components or an empty nest (subject to the existing bAllowEmptyNestIndex setting). Exactly one component blocks the start and produces a warning identifying the missing component on a two-hand attempt. Correcting the load clears the warning; the operator must release and actuate both hands again. Reset acknowledges warnings without granting permission for a single-component load. Manual tooling commands retain their existing behaviour.

The load is rechecked through validation and the final automatic move request. Presence is a start condition, not a continuous motion permissive: the sensors clearing as the table leaves Operator must not interrupt an accepted index. Existing safety and two-hand movement supervision remain in FB_IndexTable4.

Provisional active-high PBUP input: GVL_EtherCAT.stTerm19_EL1809.iEL1809_Ch1 -> GVL_IO.stInputs.bLoadingStationPbupPresent -> GVL_MASTER.stInputs -> GVL_HMI.stStatus. The terminal channel already has its PLC I/O link; this change adds application mapping, not a new hardware link. Product remains the existing Term7 Input12 signal. The unrelated PBUP magnet/tooling sensor is unchanged. Confirm sensor polarity and final terminal assignment during wiring.

Main.content has two native condition-bound indicators: TcHmiHtmlHost_OperatorNestPartPresent1 (PBUP, left), TcHmiHtmlHost_OperatorNestPartPresent2 (Product, right). Both use saved ADS mappings and native actions; no JavaScript. The unreferenced Main_b.content backup is unchanged.

## Nest memory and affected consumers

ST_Nest.bPartPresent retains product semantics. bPbupPresent stores the current Operator observation and last observation elsewhere. bLoadSetComplete records a paired load, preserved on return of an inspected/reprocess product: the PBUP may already be assembled and absent from its original pocket. Patch, Heat Stake and Vision automatic processing additionally require paired-load history. A PBUP-only disabled nest also blocks automatic indexing.

Product removal and reject chute proof retain their existing product-only semantics; leaving a loose PBUP does not discard a valid product rejection. A loose PBUP still prevents the next index. Protected result and count history survive early reload until the Operator exchange permits a new product identity. Clearing the returned Operator record requires both sensors empty. Statistics count one product, not two components; result lamps remain associated with product presence.

Fields were appended to ST_PhysicalInputs, ST_MachineInputs, ST_HmiStatus, ST_OperatorStationStatus and ST_Nest. All local callers and HMI type definitions/mappings were adapted. ST_Nest array layout changes: rebuild ADS consumers; do not assume compatibility of external clients using fixed byte offsets. No persistent nest-record layout exists in GVL_Persistent. New paired-load fields default FALSE, so existing in-flight records are not established as valid paired loads. Commission with the machine emptied and its process state reinitialised. A sensor at Operator cannot establish whether PBUP is later lost at another station; existing inspection still determines process quality.

## Offline evidence

- Final PLC build: successful, zero failed projects. Existing Safety-project ADS timeout warning 1861 remains; older hardware Error List entries are not compiler errors from this build.
- HMI Release build: successful, zero failed projects.
- check_two_parts.py executes saved Operator/ProcessCycle/NestManager branches with scripted inputs, including actual result finalisation. Four presence combinations, either load order, fresh two-hand requirement, validation/request timing gaps, accepted-move sensor loss, returned assembled product, reject exchange, four physical nest identities and one-time statistics passed. Native HMI bindings/type definitions and warning classification/mapping checks also pass.
- verify_saved.py compares all 16 modified PLC sections with final XAE readback. Full-source comparison normalises line endings and the pre-existing degree-symbol encoding discrepancy only.
- Scoped whitespace check passed. Existing unrelated tracked/untracked work and generated artifacts were preserved.

## Required supervised machine validation

With the table stationary/locked and tooling safe, verify all four sensor combinations: empty and complete loads can index with normal permissives; product-only warns PBUP missing; PBUP-only warns product missing. Load in both orders. Hold hands after correction and confirm no start until release/re-actuation. Reset an active warning and confirm a partial load remains blocked. Remove a component between trigger, validation and move request and confirm no queued movement. During an accepted index, normal sensor dropout must not create a load fault; existing two-hand release protection must still work.

Exercise all four nest IDs through good, bad and reprocess returns, including an assembled PBUP absent from its pocket, product removal, reject chute proof, early reload, remaining loose PBUP, empty exchange and repeated result publication. Verify physical identity and exactly one product count. Check disabled nests with PBUP-only loads, unknown index position/mapping freeze, stop/reset/mode transitions, door/safety/air loss using the existing approved commissioning procedure. Verify manual controls and HMI indicators on the actual browser. Designer rendering and live ADS operation have not been verified.

Deployment needs the updated PLC and a new HMI publication. No new I/O link was changed here; if the final wiring requires changing links, Activate Configuration is required after engineering review, as previously agreed. Source builds do not establish physical or safety validation.
