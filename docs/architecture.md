# System Architecture

## Overview

The dashboard follows the classic performance engineering loop:

```
Collect → Observe → Analyze → Detect Bottleneck → Visualize
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Linux Host                           │
│  /proc/stat  /proc/meminfo  CPU HW counters  Disk IO   │
└──────────────────────┬──────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   Collectors    │  psutil, /proc, perf
              └────────┬────────┘
                       │ every 5s
              ┌────────▼────────┐
              │  Metrics Engine │  collect_all()
              └────────┬────────┘
                  ┌────┴────┐
                  │         │
         ┌────────▼──┐  ┌───▼──────────┐
         │  SQLite   │  │  Analyzer    │  bottleneck detection
         │  (history)│  │  (real-time) │
         └───────────┘  └───┬──────────┘
                            │
                   ┌────────▼────────┐
                   │   FastAPI       │
                   │  REST + WS API  │
                   └────────┬────────┘
                            │ WebSocket (2s)
                   ┌────────▼────────┐
                   │  React Frontend │
                   │  Recharts       │
                   └─────────────────┘
```

## Data Flow

### Real-time Path (WebSocket)
1. Frontend connects to `ws://localhost:8000/ws/metrics`
2. Backend calls `collect_all()` every 2 seconds
3. Runs `analyze()` on the snapshot
4. Sends `{metrics, bottlenecks}` JSON to all connected clients
5. React updates charts and stat cards (no re-render flicker — `isAnimationActive=false`)

### Persistence Path (Background Task)
1. `collector_task.py` runs as an asyncio background task
2. Collects metrics every 5 seconds
3. Writes `MetricSnapshot` row to SQLite
4. If bottlenecks detected, writes `BottleneckEvent` rows
5. Frontend can query `/api/metrics/history` for trend analysis

### Benchmark Path
1. User clicks "CPU / Memory / Disk" button in UI
2. Frontend POSTs to `/api/benchmark/{type}`
3. Backend spawns subprocess (sysbench / fio) via `asyncio.create_subprocess_exec`
4. Parses stdout, saves result to `BenchmarkResult` table
5. Returns structured JSON to frontend

### Profiling Path (perf + FlameGraph)
1. User sets optional PID + duration, clicks "perf stat" or "FlameGraph"
2. Backend runs `sudo perf record -F 99 -g ...` via subprocess
3. Pipes output through `stackcollapse-perf.pl` → `flamegraph.pl`
4. Saves SVG to `flamegraphs/` directory
5. Returns URL; frontend embeds SVG in an `<iframe>`

## Why Async Throughout?

- FastAPI is async-native
- Benchmark runs (sysbench, fio, perf) can take 10–30 seconds
- Using `asyncio.create_subprocess_exec` means the server never blocks
- Other WebSocket clients keep receiving metrics while a benchmark runs

## Database Schema

```
metric_snapshots     — one row per 5s collection cycle
benchmark_results    — one row per benchmark run
bottleneck_events    — one row per detected bottleneck
```

SQLite is sufficient here because:
- Single-machine deployment
- Write rate is low (1 row/5s)
- No concurrent writers
- Easy to inspect with any SQLite browser
