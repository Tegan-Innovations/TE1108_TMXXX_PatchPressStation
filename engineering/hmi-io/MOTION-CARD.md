# EL7201 motion diagnostic card

The three EL7201 contents now use 1CH_Motion_Interface_CARD, a native
1080 x 480 UserControl with visible designer parameter bindings. Its image,
terminal text and operational LED follow the existing analog card header.
The LED uses the existing terminal bTerminalOperational, computed by
FB_TerminalInfo as TRUE only for state 8. It does not indicate axis readiness.

Two columns show actual position, velocity and torque, position difference,
set position/velocity, target position, NC axis ID, NC movement/homing states,
NC error code, application axis error/error ID, enabled, operational, homed,
moving and standstill. Actual and set values bind directly to Axis.NcToPlc;
application fields remain separately labelled. NC members and types were
checked against the generated PatchPress.tmc and current IEC declarations.
Position/velocity use configured axis units; torque retains NC reported units
without claiming Nm. Codes/states display decimal integers. Continuous values
display three decimals. All numeric controls are disabled; no command/reset
actions or PLC changes were added.

Term15/16/17 bind respectively to AxisDriveMotor, AxisPatchFeedRollMotor and
AxisWasteRollMotor, preserving the current NC mapping. New ADS mappings have
read-only access. Old application actual-value mappings remain available for
other consumers; these pages now read the NC feedback directly.

Validation: check_io.py passed for 242 active symbols and complete motion
parameter bindings. HMI Release offline build passed with zero failed projects.
No deployment or live ADS validation was performed.

Supervised acceptance: open each terminal page and compare its axis ID and all
NC values against XAE; check labels, three-decimal formatting and absence of
editable controls. Verify terminal state 8/non-8 transitions update the header
LED separately from axis readiness. Compare existing error, stopped, moving and
homing conditions with NC/application diagnostics. Verify ADS loss is shown as
a communication problem. Rendering, torque feedback availability and configured
units require site confirmation; do not induce motion/faults through this card.
