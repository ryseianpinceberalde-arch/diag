# Diagnostics and health

The existing health engine evaluates disk, memory, temperature, network latency, packet loss, SMART state, and offline state. High CPU requires five consecutive readings in the predictive scorer; repeated RAM pressure also requires multiple readings. Alert keys are stable and active alerts are updated rather than recreated.

The health score service returns a 0–100 estimate with labels: Excellent, Healthy, Warning, Poor, or Critical. Missing battery and temperature sensors are omitted from the weighted denominator instead of being treated as zero.

Thresholds are stored in `app_settings` and edited through the existing Settings page/API. Sensor absence is represented as null or unavailable; the agent does not invent temperatures or battery values.
