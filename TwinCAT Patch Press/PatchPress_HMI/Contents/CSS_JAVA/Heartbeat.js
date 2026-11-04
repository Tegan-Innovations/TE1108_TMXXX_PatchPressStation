
// Existing JS exception: serialize ADS writes and expose timing/error evidence.
// Browser stalls and communication loss must still expire the PLC watchdog.
(function () {
    'use strict';
    if (window.PatchPressHeartbeat) {
        return; // A dependency loaded twice must not create two writers.
    }
    if (window.heartbeatInterval !== undefined && window.heartbeatInterval !== null) {
        window.clearInterval(window.heartbeatInterval);
    }

    var symbol = '%s%ADS.PLC1.GVL_HMI.bHMIAlive%/s%';
    var nextValue = true;
    var status = {
        intervalMs: 250, inFlight: false, sent: 0, acknowledged: 0,
        errors: 0, lastError: null, lastTickAt: 0, lastTickGapMs: 0,
        maxTickGapMs: 0, lastRequestAt: 0, lastAckAt: 0,
        lastWriteLatencyMs: 0, maxWriteLatencyMs: 0
    };
    window.PatchPressHeartbeat = status;
    function now() { return new Date().getTime(); }

    function tick() {
        var time = now();
        if (status.lastTickAt) {
            status.lastTickGapMs = time - status.lastTickAt;
            status.maxTickGapMs = Math.max(status.maxTickGapMs, status.lastTickGapMs);
        }
        status.lastTickAt = time;
        if (status.inFlight) {
            return; // No queued writes or phase changes without a reply.
        }
        if (typeof TcHmi === 'undefined' || !TcHmi.Symbol || !TcHmi.Symbol.writeEx) {
            status.lastError = 'HMI symbol API not ready';
            return;
        }

        var value = nextValue;
        var finished = false;
        status.inFlight = true;
        status.lastRequestAt = time;
        status.sent += 1;
        try {
            // Installed API: writeEx(expression, value, callback).
            TcHmi.Symbol.writeEx(symbol, value, function (data) {
                if (finished) { return; }
                finished = true;
                status.inFlight = false;
                status.lastWriteLatencyMs = now() - time;
                status.maxWriteLatencyMs = Math.max(status.maxWriteLatencyMs, status.lastWriteLatencyMs);
                if (data && data.error === TcHmi.Errors.NONE) {
                    status.lastAckAt = now();
                    status.acknowledged += 1;
                    status.lastError = null;
                    nextValue = !value;
                } else {
                    status.errors += 1;
                    status.lastError = data ? data.error : 'Missing write response';
                    // Retry the same phase: a failed write is not a heartbeat.
                }
            });
        } catch (error) {
            if (!finished) {
                finished = true;
                status.inFlight = false;
                status.errors += 1;
                status.lastError = String(error);
            }
        }
    }

    window.heartbeatInterval = window.setInterval(tick, status.intervalMs);
    tick();
}());

