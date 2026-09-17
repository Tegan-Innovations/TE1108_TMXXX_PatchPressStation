// Keep these lines for a best effort IntelliSense in the editor.
/// <reference path="./../../../TE1108_Kistler/Packages/Beckhoff.TwinCAT.HMI.Framework.14.3.431/runtimes/native1.12-tchmi/TcHmi.d.ts" />
/// <reference path="./../../../Packages/Beckhoff.TwinCAT.HMI.Framework.14.3.431/runtimes/native1.12-tchmi/TcHmi.d.ts" />

// Keep these lines for a best effort IntelliSense in the editor.
/// <reference path="./../../../TE1108_Kistler/Packages/Beckhoff.TwinCAT.HMI.Framework.14.3.431/runtimes/native1.12-tchmi/TcHmi.d.ts" />
/// <reference path="./../../../Packages/Beckhoff.TwinCAT.HMI.Framework.14.3.431/runtimes/native1.12-tchmi/TcHmi.d.ts" />

window.confirmManualMode = function () {
    try {
        const machineStateSymbol =
            '%s%ADS.PLC1.GVL_MASTER.stMachineStatus.eMachineState%/s%';

        const manualModeRequestSymbol =
            '%s%ADS.PLC1.GVL_HMI.i_bHMIManualModeRequest%/s%';

        TcHmi.Symbol.readEx2(machineStateSymbol, function (dataState) {

            if (dataState.error !== TcHmi.Errors.NONE) {
                closeMainPopup();

                setTimeout(function () {
                    alert("HMI Error: Failed to read Machine State. Code: " + dataState.error);
                }, 100);

                return;
            }

            const machineStateValue =
                dataState.value !== undefined ? dataState.value : dataState.result;

            const isReadyToStart =
                machineStateValue === 3 ||
                String(machineStateValue).toUpperCase().includes("SYSTEM_READY_TO_START");

            const isAlreadyManualMode =
                machineStateValue === 6 ||
                String(machineStateValue).toUpperCase().includes("MANUAL_MODE");

            if (isAlreadyManualMode) {
                closeMainPopup();

                goToManualModePage();

                setTimeout(function () {
                    alert("The system is already in Manual Mode.");
                }, 100);

                return;
            }

            if (isReadyToStart) {

                // Send the Manual Mode request to the PLC.
                TcHmi.Symbol.writeEx2(manualModeRequestSymbol, true, function (dataWrite) {
                    if (dataWrite.error !== TcHmi.Errors.NONE) {
                        setTimeout(function () {
                            alert("HMI Error: Failed to request Manual Mode. Code: " + dataWrite.error);
                        }, 100);
                    }
                });

                // Close the popup and change the screen without waiting for the write callback.
                closeMainPopup();

                goToManualModePage();

                setTimeout(function () {
                    alert("The system has entered Manual Mode.");
                }, 100);

                return;

            } else {
                closeMainPopup();

                setTimeout(function () {
                    alert("Manual Mode blocked: The system is not in Ready To Start, so it cannot enter Manual Mode.");
                }, 100);

                return;
            }
        });

    } catch (error) {
        closeMainPopup();

        setTimeout(function () {
            alert("Fatal Application Exception: " + error.message);
        }, 100);
    }
};


window.closeMainPopup = function () {
    try {
        const popup = TcHmi.Controls.get('Main_Popup');

        if (popup) {
            popup.close();
        } else {
            console.log("Main_Popup control not found.");
        }

    } catch (error) {
        console.log("Failed to close Main_Popup: " + error.message);
    }
};


window.goToManualModePage = function () {
    try {
        const mainRegion = TcHmi.Controls.get('Main_Region');

        if (mainRegion) {
            mainRegion.setTargetContent('Contents/Screens/Manual_Mode.content');
        } else {
            console.log("Main_Region control not found.");
        }

    } catch (error) {
        console.log("Failed to change Main_Region content: " + error.message);
    }
};