# API Reference

Base URL: `http://localhost:8000`

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## WebSocket

| Endpoint | Description |
|---|---|
| `WS /ws/metrics` | Live metrics + bottlenecks stream, pushed every 2 seconds |

**Message format:**
```json
{
  "metrics": {
    "timestamp": 1715678400.0,
    "cpu": { "percent": 23.4, "per_core": [18.2, 28.6], "freq_mhz": 2400.0, "count_logical": 4 },
    "memory": { "percent": 61.2, "used_gb": 4.9, "available_gb": 3.1, "total_gb": 8.0, "swap_percent": 0.0 },
    "disk": { "percent": 54.3, "used_gb": 108.6, "total_gb": 200.0, "read_mb": 12043.2, "write_mb": 8921.4 },
    "network": { "sent_mb": 234.1, "recv_mb": 891.3 },
    "load": { "avg_1": 1.2, "avg_5": 0.9, "avg_15": 0.7 },
    "io_wait": 3.2,
    "processes": [{ "pid": 1234, "name": "python3", "cpu_percent": 45.2, "memory_percent": 2.1 }]
  },
  "bottlenecks": [
    { "resource": "cpu", "severity": "warning", "value": 87.3, "message": "CPU usage at 87.3% — warning saturation detected" }
  ]
}
```

---

## Metrics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/metrics/snapshot` | Single real-time snapshot (same shape as WebSocket metrics object) |
| `GET` | `/api/metrics/history?limit=60` | Last N snapshots from SQLite |
| `GET` | `/api/metrics/bottlenecks` | Recent bottleneck events from DB |

---

## Benchmarks

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/benchmark/cpu?threads=4&duration=10` | Run sysbench CPU benchmark |
| `POST` | `/api/benchmark/memory?duration=10` | Run sysbench memory benchmark |
| `POST` | `/api/benchmark/disk?duration=10` | Run fio disk benchmark |
| `GET` | `/api/benchmark/history` | Past benchmark results from DB |

**Response example (CPU benchmark):**
```json
{
  "tool": "sysbench",
  "type": "cpu",
  "threads": 4,
  "duration_sec": 10,
  "results": { "events_per_second": 3241.87, "latency_avg_ms": 1.23 },
  "summary": "3241.87 events/sec, avg latency 1.23ms"
}
```

---

## Profiler

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/profiler/perf-stat?pid=&duration=5` | Run `perf stat` (system-wide if no PID) |
| `POST` | `/api/profiler/flamegraph?pid=&duration=10` | Generate FlameGraph SVG |
| `GET` | `/flamegraphs/<filename>.svg` | Serve a generated SVG file |

**perf-stat response example:**
```json
{
  "cycles": 10432891,
  "instructions": 12891234,
  "cache_misses": 45231,
  "cache_references": 1932441,
  "branch_misses": 12891,
  "branches": 1445231,
  "ipc": 1.24
}
```

**flamegraph response example:**
```json
{
  "url": "/flamegraphs/flamegraph_1715678400.svg",
  "filename": "flamegraph_1715678400.svg"
}
```
