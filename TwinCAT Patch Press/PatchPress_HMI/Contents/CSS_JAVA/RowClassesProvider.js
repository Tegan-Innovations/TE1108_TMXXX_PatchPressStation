// Keep these lines for a best effort IntelliSense of Visual Studio 2017 and higher.
/// <reference path="./../../Packages/Beckhoff.TwinCAT.HMI.Framework.12.762.46/runtimes/native1.12-tchmi/TcHmi.d.ts" />

(function (/** @type {globalThis.TcHmi} */ TcHmi) {
    var Functions;

    (function (/** @type {globalThis.TcHmi.Functions} */ Functions) {
        var TcHmiProject1;

        (function (TcHmiProject1) {

            function RowClassesProvider(RowData, RowIndex, RowNumber) {
                var cssStyles = [];

                if (!RowData) {
                    return cssStyles;
                }

                var rawType = RowData.sType;

                /*
                 * Normalizes both possible formats:
                 *
                 * Numeric:
                 * 1, 2, 3, 4
                 *
                 * Text:
                 * Fault
                 * Cycle Stop Fault
                 * Cycle Stop Request
                 * Message
                 */
                var typeNumber;

                if (typeof rawType === "number") {
                    typeNumber = rawType;
                } else {
                    var normalizedType = String(rawType || "")
                        .trim()
                        .toLowerCase();

                    switch (normalizedType) {
                        case "1":
                        case "fault":
                        case "alarm":
                            typeNumber = 1;
                            break;

                        case "2":
                        case "cycle stop fault":
                            typeNumber = 2;
                            break;

                        case "3":
                        case "cycle stop request":
                        case "alert":
                            typeNumber = 3;
                            break;

                        case "4":
                        case "message":
                            typeNumber = 4;
                            break;

                        default:
                            typeNumber = 0;
                            break;
                    }
                }

                switch (typeNumber) {
                    case 1:
                    case 2:
                        cssStyles.push("Alarm");
                        break;

                    case 3:
                        cssStyles.push("Alert");
                        break;

                    case 4:
                        cssStyles.push("Message");
                        break;
                }

                return cssStyles;
            }

            TcHmiProject1.RowClassesProvider = RowClassesProvider;

        })(TcHmiProject1 =
            Functions.TcHmiProject1 ||
            (Functions.TcHmiProject1 = {}));

    })(Functions =
        TcHmi.Functions ||
        (TcHmi.Functions = {}));

})(TcHmi);

TcHmi.Functions.registerFunctionEx(
    "RowClassesProvider",
    "TcHmi.Functions.TcHmiProject1",
    TcHmi.Functions.TcHmiProject1.RowClassesProvider
);