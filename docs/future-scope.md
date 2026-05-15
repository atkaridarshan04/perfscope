# Future Scope

Planned improvements and features not yet implemented.

---

## AI / ML Integration

### Anomaly Detection
Replace fixed thresholds in `analyzer.py` with a trained model (e.g., Isolation Forest or LSTM autoencoder) that learns the system's normal behavior and flags statistical anomalies. This would catch subtle degradation that threshold rules miss — for example, CPU at 70% that is unusually high for a Sunday night.

### Predictive Alerting
Train a time-series forecasting model (Prophet, ARIMA, or a simple LSTM) on the `metric_snapshots` table to predict resource exhaustion before it happens. Example: "Disk will reach 95% in ~4 hours at current write rate."

### Root Cause Correlation
Use correlation analysis across metrics to automatically suggest root causes. Example: when IO wait spikes, correlate with which process had the highest disk write rate at the same timestamp, and surface that in the alert message.

### Natural Language Query Interface
Add an LLM-backed endpoint (`POST /api/ask`) that accepts plain-English questions about system state and history:
- "What caused the CPU spike at 3pm?"
- "Which process has been using the most memory this week?"
- "Is my disk performance degrading over time?"

The LLM would query the SQLite history and return a structured answer.

### Intelligent Benchmark Recommendations
After collecting a baseline profile, suggest which benchmark to run next based on observed bottlenecks. If IO wait is consistently high, recommend the disk benchmark. If IPC from `perf stat` is low, recommend a FlameGraph.

---

## Monitoring Improvements

### Multi-machine Support
Replace SQLite with TimescaleDB or InfluxDB and add a lightweight agent that can run on remote machines, shipping metrics to a central backend. The current architecture is single-machine only.

### Alert Notifications
Integrate with Slack, PagerDuty, or email to push critical bottleneck alerts outside the dashboard (currently alerts are only visible if the dashboard is open).

### Custom Threshold Configuration
Expose the bottleneck thresholds via a settings UI and persist them to a config file, instead of hardcoding them in `analyzer.py`.

### Network Bottleneck Detection
Extend the analyzer to detect network saturation — currently network bytes are collected but not analyzed for bottlenecks.

---

## Profiling Improvements

### Continuous Profiling
Run `perf record` as a low-overhead continuous background process (similar to Pyroscope or Parca) instead of on-demand, so you always have a FlameGraph available for any time window.

### Python-level Profiling
Add `py-spy` integration for Python process profiling — generates FlameGraphs at the Python function level rather than the native/kernel level, which is more useful for Python application developers.

---

## Frontend Improvements

### Dark/Light Theme Toggle
Currently hardcoded dark theme in `App.css`.

### Exportable Reports
Allow exporting a PDF or JSON report of a monitoring session — metrics history, benchmark results, and bottleneck events — for sharing or archiving.

### Configurable Dashboard Layout
Let users pin/unpin panels and reorder them.
