# Settings navigation enabled only in Stopped

Machine Cyclic now publishes bEnableSetting only for E_MachineState.Stopped; removed the former Manual alternative. PRG_HmiStatus copies this to GVL_HMI.stStatus.bEnableSettings; Menu.content Settings button IsEnabled is already bound to it. No HMI source changes needed. This controls navigation availability; individual settings Apply conditions remain owned by their existing PLC handlers.

Validation: fresh snapshot, hash-checked preview/write, XAE readback, saved-source one-line synchronization and scoped diff check. Offline PLC build succeeded with zero failed projects. No runtime connection, PLC download, publication or commit performed.

After authorized PLC download, verify Settings enabled in Stopped and disabled in Manual, ReadyToStart, AutoCycle, Initialising, Stopping, Fault and PowerUp. Verify existing initialization navigation returns to Main when leaving Settings for initialization. No physical machine test performed by the agent.
