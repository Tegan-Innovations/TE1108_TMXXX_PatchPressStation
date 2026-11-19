# HMI mapping correction — 2026-11-06

This correction supersedes the older terminal-number statements in HANDOVER.md.
The saved EtherCAT configuration contains Term19 EL1809, Term20 EL4028,
Term21 **EL3314-0092**, Term22 EL6633 and Term23 EL9011. The requested
EL3341-0092 spelling differs from the actual project; the HMI follows the project.

Main_IOs uses those physical identities and their matching content paths.
The PLC symbols remain unchanged: physical Term20 uses stTerm21_EL4028,
physical Term21 uses stTerm20_EL3314, and physical Term22 uses stTerm21_EL6633.
These bindings were verified against the current OwnerB/Link destinations.
Term21's legacy IVEK page was replaced with all four actual thermocouple channels.
Term22 uses the existing mapped terminal status. The misleading EK1100 detail
image was removed from that page. No substitute hardware image was invented.
Unused legacy hardware contents and superseded duplicate pages are excluded from
the HMI project; their historical files remain on disk. No PLC, I/O link, NC or
TwinSAFE changes were made by this correction.

Validation: check_io.py passed, including all 197 typed symbols, physical channel
destinations, exact terminal navigation and absence of legacy references in all
included hardware contents. Its historical link comparison now accounts for the
hardware owner renumbering already present before this correction. HMI Release
offline build completed with zero failed projects; see corrected-hmi-build-result.json.
Scoped git diff --check passed. Unrelated existing workspace edits were preserved.

Browser/designer rendering and live ADS feedback were not verified. Before use,
select each terminal in Main_IOs, confirm its channel labels/values against XAE,
and confirm Term20 pressure output, Term21 thermocouples, Term22 status and passive
Term23 load correctly. Verify the pages remain read-only in manual and automatic
modes. No publish, runtime connection, activation, download or commit performed.
