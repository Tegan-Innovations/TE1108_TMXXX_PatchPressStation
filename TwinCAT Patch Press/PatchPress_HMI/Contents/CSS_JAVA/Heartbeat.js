
var heartbeatInterval = null;

heartbeatInterval = setInterval(function () {

        TcHmi.Symbol.readEx2('%s%ADS.PLC1.GVL_HMI.bHMIAlive%/s%', function (data) {

            if (data.error === TcHmi.Errors.NONE) {

                TcHmi.Symbol.writeEx('%s%ADS.PLC1.GVL_HMI.bHMIAlive%/s%', !data.value);
                
            }
        });

    }, 1000); // 1 second

