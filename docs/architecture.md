# Architecture

## Overview

The dashboard follows the standard performance engineering loop:

```
Collect → Observe → Analyze → Detect Bottleneck → Visualize
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Linux Host                         │
│   /proc/stat   /proc/meminfo   CPU HW counters          │
└──────────────────────┬──────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   Collectors    │  psutil + /proc reader
              │  system.py      │
              └────────┬────────┘
                       │ collect_all() → metrics dict
                  ┌────┴────┐
                  │         │
         ┌────────▼──┐  ┌───▼──────────┐
         │  SQLite   │  │   Analyzer   │  threshold-based
         │  history  │  │  analyzer.py │  bottleneck detection
         └───────────┘  └───┬──────────┘
                            │
                   ┌────────▼────────┐
                   │    FastAPI      │
                   │  REST + WS API  │
                   └────────┬────────┘
                            │ WebSocket (2s push)
                   ┌────────▼────────┐
                   │ React Frontend  │
                   │ Recharts        │
                   └─────────────────┘
```

---

## Data Flows

### Real-time (WebSocket)

1. Frontend connects to `ws://localhost:8000/ws/metrics`
2. Backend calls `collect_all()` every 2 seconds
3. Runs `analyze()` on the snapshot
4. Pushes `{metrics, bottlenecks}` JSON to all connected clients
5. React updates charts and stat cards (`isAnimationActive=false` prevents flicker)

### Persistence (Background Task)

1. `collector_task.py` runs as an asyncio background task
2. Collects metrics every 5 seconds (slower than WebSocket to limit DB growth)
3. Writes `MetricSnapshot` row to SQLite
4. If bottlenecks detected, writes `BottleneckEvent` rows
5. Frontend queries `/api/metrics/history` for trend charts

### Benchmark Path

1. User clicks a benchmark button in the UI
2. Frontend POSTs to `/api/benchmark/{type}`
3. Backend spawns subprocess (`sysbench` / `fio`) via `asyncio.create_subprocess_exec`
4. Parses stdout, saves result to `BenchmarkResult` table
5. Returns structured JSON to frontend

### Profiling Path (perf + FlameGraph)

1. User sets optional PID + duration, clicks "perf stat" or "FlameGraph"
2. Backend runs `sudo perf record -F 99 -g ...` via subprocess
3. Pipes output through `stackcollapse-perf.pl` → `flamegraph.pl`
4. Saves SVG to `flamegraphs/` directory, served as a static file
5. Frontend embeds the SVG in an `<iframe>`

---

## Database Schema

SQLite file: `backend/metrics.db`

**metric_snapshots** — one row every 5 seconds
```
id | timestamp | cpu_percent | memory_percent | swap_percent | disk_percent | load_avg_1 | io_wait | ...
```

**benchmark_results** — one row per benchmark run
```
id | timestamp | bench_type | tool | duration_sec | summary | result_json
```

**bottleneck_events** — one row per detected bottleneck
```
id | timestamp | resource | severity | value | message
```

Inspect directly:
```bash
sqlite3 backend/metrics.db
.tables
SELECT * FROM metric_snapshots ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM bottleneck_events ORDER BY timestamp DESC LIMIT 10;
```

---

## Why Async Throughout?

Benchmark runs (sysbench, fio, perf) take 10–30 seconds. Using `asyncio.create_subprocess_exec` means the FastAPI server never blocks — other WebSocket clients keep receiving live metrics while a benchmark runs in the background.

---

## File Reference

```
backend/app/
├── main.py               Entry point. Registers routes, starts background task,
│                         mounts static files, configures CORS.
├── core/database.py      SQLAlchemy async engine. Creates DB on startup.
│                         Provides get_db() dependency for route handlers.
├── models/metrics.py     Three ORM models: MetricSnapshot, BenchmarkResult, BottleneckEvent
├── collectors/system.py  All psutil calls + /proc/stat IO wait parser.
│                         collect_all() → single metrics dict.
├── services/
│   ├── analyzer.py       Threshold-based bottleneck detection.
│   ├── benchmark.py      Async subprocess wrappers for sysbench and fio.
│   ├── profiler.py       perf record → perf script → stackcollapse → flamegraph pipeline.
│   └── collector_task.py Background asyncio task. Runs every 5s, writes to SQLite.
└── api/
    ├── ws.py             WebSocket /ws/metrics — pushes metrics every 2s.
    ├── metrics.py        REST: snapshot, history, bottleneck history.
    ├── benchmark.py      REST: trigger benchmarks, get history.
    └── profiler.py       REST: perf stat, flamegraph generation.

frontend/src/
├── App.jsx               Root layout. Assembles all components.
├── App.css               All styles (dark theme, responsive grid).
├── hooks/useMetrics.js   WebSocket hook. Manages connection, history array, auto-reconnect.
├── api/client.js         fetch() wrappers for all REST endpoints.
└── components/
    ├── cards/
    │   ├── StatCard.jsx          Single metric card (value + subtitle).
    │   └── BottleneckAlert.jsx   Warning/critical alert banners.
    ├── charts/
    │   ├── MetricsChart.jsx      Recharts LineChart — 4 metrics over time.
    │   └── CpuCoresChart.jsx     Recharts BarChart — per-core utilization.
    └── panels/
        ├── ProcessTable.jsx      Top 10 processes table, live.
        ├── BenchmarkPanel.jsx    Benchmark trigger buttons + results list.
        └── ProfilerPanel.jsx     perf stat + FlameGraph controls + display.
```
