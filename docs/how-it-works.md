# How It All Works — End-to-End Project Walkthrough

> Read this from top to bottom. By the end you will understand exactly how every tool works,
> what commands run under the hood, how they connect to the dashboard, and how to explain
> this project confidently in an interview.

---

## 1. The Problem This Project Solves

When a Linux system becomes slow, the typical developer reaction is:

```
"Something is slow… let me restart the server."
```

That is debugging blindly. A performance engineer asks instead:

```
Is it the CPU? Memory? Disk? Network? A single process? The kernel scheduler?
```

This project gives you the tools to answer that question — in real time, visually,
with automatic bottleneck detection and the ability to drill down to the exact function
causing the problem.

---

## 2. The Big Picture — What Runs When You Start the Project

When you run the project, two processes start:

```
Terminal 1: uvicorn app.main:app --reload      ← Python backend on port 8000
Terminal 2: npm run dev                         ← React frontend on port 5173
```

The moment the backend starts, three things happen automatically:

1. **SQLite database is created** (`backend/metrics.db`) with three tables
2. **Background collector task starts** — collects system metrics every 5 seconds and writes to DB
3. **FastAPI begins listening** for WebSocket connections and REST API calls

The moment you open the browser at `http://localhost:5173`:

1. React app loads
2. `useMetrics.js` hook opens a WebSocket to `ws://localhost:8000/ws/metrics`
3. Backend starts pushing a JSON snapshot every 2 seconds
4. Charts and cards update live

---

## 3. Layer by Layer — How Each Part Works

---

### Layer 1: The Linux Kernel (Data Source)

Everything starts here. Linux tracks system state internally and exposes it through
the `/proc` virtual filesystem — files that don't exist on disk but are generated
by the kernel on-the-fly when read.

```bash
# Try these yourself:
cat /proc/stat          # raw CPU time counters
cat /proc/meminfo       # memory and swap details
cat /proc/loadavg       # load averages
cat /proc/diskstats     # disk IO counters
```

Example `/proc/stat` output:
```
cpu  4705 0 1142 282700 1032 0 45 0 0 0
cpu0 1234 0 300  70000  250 0 10 0 0 0
cpu1 1200 0 280  71000  260 0 12 0 0 0
...
```

The fields are: `user nice system idle iowait irq softirq steal guest guest_nice`

Our code reads `iowait` (field 5) and `total` to compute IO wait percentage:
```python
# backend/app/collectors/system.py
iowait% = (iowait_ticks / total_ticks) * 100
```

The CPU also has hardware performance counters built into the silicon — registers
that count cycles, instructions, cache misses, etc. These are NOT in `/proc`.
They require the `perf` tool to access.

---

### Layer 2: Collectors (`backend/app/collectors/system.py`)

This file is the bridge between the Linux kernel and our application.
It uses `psutil` — a Python library that wraps `/proc` reads into clean function calls.

**What psutil does under the hood:**

| Our call | psutil reads | Kernel source |
|---|---|---|
| `psutil.cpu_percent()` | `/proc/stat` | CPU time counters |
| `psutil.virtual_memory()` | `/proc/meminfo` | RAM stats |
| `psutil.swap_memory()` | `/proc/meminfo` | Swap stats |
| `psutil.disk_io_counters()` | `/proc/diskstats` | Block device IO |
| `psutil.net_io_counters()` | `/proc/net/dev` | Network interface stats |
| `psutil.process_iter()` | `/proc/<pid>/stat` | Per-process stats |
| `psutil.getloadavg()` | `/proc/loadavg` | Load averages |

The main function `collect_all()` calls all of these and returns one dictionary:

```python
{
  "timestamp": 1715678400.0,
  "cpu": {
    "percent": 23.4,
    "per_core": [18.2, 28.6, 21.0, 25.8],
    "freq_mhz": 2400.0,
    "count_logical": 4,
    "count_physical": 2
  },
  "memory": {
    "percent": 61.2,
    "used_gb": 4.9,
    "available_gb": 3.1,
    "total_gb": 8.0,
    "swap_percent": 0.0,
    "swap_used_gb": 0.0,
    "swap_total_gb": 2.0
  },
  "disk": {
    "percent": 54.3,
    "used_gb": 108.6,
    "total_gb": 200.0,
    "read_mb": 12043.2,
    "write_mb": 8921.4
  },
  "network": { "sent_mb": 234.1, "recv_mb": 891.3, ... },
  "load": { "avg_1": 1.2, "avg_5": 0.9, "avg_15": 0.7 },
  "io_wait": 3.2,
  "processes": [
    { "pid": 1234, "name": "python3", "cpu_percent": 45.2, "memory_percent": 2.1, "status": "running" },
    ...
  ]
}
```

This single dictionary is the foundation for everything else.

---

### Layer 3: The Analyzer (`backend/app/services/analyzer.py`)

The analyzer takes the raw metrics dictionary and converts numbers into insights.

**This is the "smart" part of the project.**

Raw metrics alone are confusing:
```
cpu_percent = 91.3
```

The analyzer converts this to:
```json
{
  "resource": "cpu",
  "severity": "critical",
  "value": 91.3,
  "message": "CPU usage at 91.3% — critical saturation detected"
}
```

**How it works — the thresholds:**

```python
# For each resource, two thresholds: warning and critical
CPU:    warning > 85%,   critical > 95%
Memory: warning > 80%,   critical > 95%
Swap:   warning > 20%,   critical > 60%   ← even 20% swap is serious
Disk:   warning > 80%,   critical > 95%
Load:   warning > 1×CPUs, critical > 2×CPUs
IOWait: warning > 20%,   critical > 40%
```

**Load average explained:**
Load average counts processes in R (running) or D (uninterruptible sleep) state.
On a 4-core machine, load = 4.0 means 100% utilized. Load = 8.0 means processes
are queuing — the system is overloaded. We normalize: `load_norm = (load1 / cpu_count) * 100`.

The analyzer returns a list of bottleneck objects. Empty list = system healthy.

---

### Layer 4: Background Persistence (`backend/app/services/collector_task.py`)

This is an `asyncio` background task that runs forever inside the FastAPI process.

```
Every 5 seconds:
  1. Call collect_all()          → get metrics dict
  2. Call analyze(metrics)       → get bottlenecks list
  3. Write MetricSnapshot to DB  → for history charts
  4. Write BottleneckEvent rows  → for alert history
```

Why every 5 seconds for DB but 2 seconds for WebSocket?
- WebSocket needs to feel live → 2s
- DB writes at 2s would grow the database very fast → 5s is enough for trend analysis

The background task uses `asyncio.create_task()` so it runs concurrently with
the web server — it never blocks incoming requests.

---

### Layer 5: The API (`backend/app/api/`)

FastAPI exposes the data through two mechanisms:

#### WebSocket — `/ws/metrics`

```
Browser ──── ws://localhost:8000/ws/metrics ────► FastAPI
             ◄──── JSON every 2 seconds ─────────
```

The WebSocket handler in `ws.py`:
```python
while True:
    metrics = collect_all()
    bottlenecks = analyze(metrics)
    await websocket.send_text(json.dumps({"metrics": metrics, "bottlenecks": bottlenecks}))
    await asyncio.sleep(2)
```

If the browser disconnects (tab closed, network drop), the `WebSocketDisconnect`
exception is caught and the connection is removed. The frontend auto-reconnects
after 3 seconds.

#### REST endpoints

| Endpoint | What it does |
|---|---|
| `GET /api/metrics/snapshot` | One-shot current metrics (no WebSocket needed) |
| `GET /api/metrics/history?limit=60` | Last 60 rows from SQLite |
| `GET /api/metrics/bottlenecks` | Recent bottleneck events from DB |
| `POST /api/benchmark/cpu` | Triggers sysbench CPU test |
| `POST /api/benchmark/memory` | Triggers sysbench memory test |
| `POST /api/benchmark/disk` | Triggers fio disk test |
| `GET /api/benchmark/history` | Past benchmark results |
| `POST /api/profiler/perf-stat` | Runs `sudo perf stat` |
| `POST /api/profiler/flamegraph` | Runs `sudo perf record` + generates SVG |
| `GET /flamegraphs/<file>.svg` | Serves generated SVG files statically |

All endpoints are documented interactively at `http://localhost:8000/docs` (Swagger UI).

---

### Layer 6: Benchmarking (`backend/app/services/benchmark.py`)

When you click a benchmark button in the UI, the backend runs a real system tool
as a subprocess. Here is exactly what runs:

#### CPU Benchmark — sysbench

```bash
sysbench cpu --threads=4 --time=10 run
```

What sysbench does: computes prime numbers up to 10,000 repeatedly using all 4 threads
for 10 seconds. This is a pure CPU workload — no disk, no network.

Real output from sysbench:
```
CPU speed:
    events per second:  3241.87

General statistics:
    total time:         10.0012s
    total number of events: 32423

Latency (ms):
         min:    0.98
         avg:    1.23
         max:    8.45
```

Our parser extracts `events_per_second`, `latency_avg_ms`, etc. and returns:
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

#### Memory Benchmark — sysbench

```bash
sysbench memory --time=10 run
```

Reads/writes memory sequentially. Measures raw memory bandwidth.

Real output:
```
102400.00 MiB transferred (9876.54 MiB/sec)
```

#### Disk Benchmark — fio

```bash
fio --name=randreadwrite --ioengine=libaio --iodepth=16 \
    --rw=randrw --bs=4k --direct=1 --size=128m \
    --runtime=10 --time_based \
    --filename=/tmp/fio_test --output-format=json
```

Breaking down the flags:
- `ioengine=libaio` — Linux async IO, most realistic for production workloads
- `iodepth=16` — 16 IO requests in flight simultaneously (simulates a busy database)
- `rw=randrw` — random mix of reads and writes (worst case for spinning disks)
- `bs=4k` — 4KB blocks (standard database page size)
- `direct=1` — bypass the OS page cache, measure actual disk speed
- `output-format=json` — machine-readable output for our parser

fio outputs a large JSON. We extract:
```json
{
  "read_bw_kb": 45231,
  "read_iops": 11307,
  "read_lat_ms": 0.712,
  "write_bw_kb": 44891,
  "write_iops": 11222,
  "write_lat_ms": 0.718
}
```

The test file `/tmp/fio_test` is deleted after the benchmark.

**Why async subprocess?**
Benchmarks take 10–30 seconds. Using `asyncio.create_subprocess_exec` means
the FastAPI server never blocks — other WebSocket clients keep receiving live
metrics while a benchmark runs in the background.

---

### Layer 7: Profiling with perf + FlameGraph (`backend/app/services/profiler.py`)

This is the most technically impressive part of the project.

#### perf stat

```bash
sudo perf stat -e cycles,instructions,cache-misses,cache-references,branch-misses,branches -- sleep 5
```

This runs for 5 seconds and counts hardware events using the CPU's built-in
Performance Monitoring Units (PMUs) — physical registers in the CPU silicon.

Real output:
```
 Performance counter stats for 'sleep 5':

      10,432,891      cycles
      12,891,234      instructions              #    1.24  insn per cycle
          45,231      cache-misses              #    2.34% of all cache refs
       1,932,441      cache-references
          12,891      branch-misses             #    0.89% of all branches
       1,445,231      branches

       5.002341234 seconds time elapsed
```

Key insight: **IPC (instructions per cycle)** = `instructions / cycles`.
- IPC close to 1.0+ = CPU is efficient
- IPC much less than 1.0 = CPU is stalling (waiting for memory, cache misses)

Our parser extracts all counters into a dictionary displayed in the Profiler panel.

#### FlameGraph Generation — 4-step pipeline

This is the full command sequence that runs when you click "FlameGraph":

**Step 1: Record stack traces**
```bash
sudo perf record -F 99 -g -a -o /tmp/perf.data -- sleep 10
```
- `-F 99` — sample 99 times per second (99Hz, not 100Hz to avoid timer lockstep)
- `-g` — record full call graphs (stack traces, not just top-level function)
- `-a` — system-wide, all CPUs (or `-p <pid>` for a specific process)
- `-o /tmp/perf.data` — save raw binary data

This creates a binary file with thousands of stack trace samples.

**Step 2: Convert to text**
```bash
sudo perf script -i /tmp/perf.data
```

Output (one sample):
```
python3 12345 [001] 12345.678: cycles:
        ffffffff81234567 __schedule+0x87 ([kernel.kallsyms])
        ffffffff81234890 schedule+0x40 ([kernel.kallsyms])
        00007f1234567890 PyEval_EvalFrameEx+0x1234 (/usr/bin/python3)
        00007f1234567abc my_function+0x45 (/home/user/app.py)
```

**Step 3: Collapse stacks**
```bash
perl /opt/FlameGraph/stackcollapse-perf.pl < perf_script_output
```

Output (one line per unique stack, with count):
```
python3;PyEval_EvalFrameEx;my_function 42
python3;PyEval_EvalFrameEx;other_function 18
```

**Step 4: Generate SVG**
```bash
perl /opt/FlameGraph/flamegraph.pl < collapsed_stacks > flamegraph_1715678400.svg
```

The SVG is an interactive file — you can click on blocks to zoom in.
It is saved to `flamegraphs/` and served by FastAPI as a static file.
The frontend embeds it in an `<iframe>`.

**The full pipeline in our code:**
```python
# profiler.py — simplified
rc, _, _ = await _run(["sudo", "perf", "record", "-F", "99", "-g", "-a",
                        "-o", "/tmp/perf.data", "--", "sleep", str(duration)])

rc, script_out, _ = await _run(["sudo", "perf", "script", "-i", "/tmp/perf.data"])

collapse = await asyncio.create_subprocess_exec(
    "perl", "/opt/FlameGraph/stackcollapse-perf.pl",
    stdin=PIPE, stdout=PIPE)
collapsed, _ = await collapse.communicate(input=script_out.encode())

flame = await asyncio.create_subprocess_exec(
    "perl", "/opt/FlameGraph/flamegraph.pl",
    stdin=PIPE, stdout=PIPE)
svg_bytes, _ = await flame.communicate(input=collapsed)

svg_path.write_bytes(svg_bytes)
```

---

### Layer 8: The Frontend (`frontend/src/`)

#### WebSocket Hook (`hooks/useMetrics.js`)

This is the heart of the frontend. It:
1. Opens a WebSocket connection on mount
2. Parses every incoming JSON message
3. Updates `latest` (current snapshot) and `history` (rolling 60-point array)
4. Auto-reconnects after 3 seconds if the connection drops

```javascript
ws.onmessage = (e) => {
  const { metrics, bottlenecks } = JSON.parse(e.data)
  setLatest(metrics)
  setBottlenecks(bottlenecks)
  setHistory(prev => [...prev.slice(-59), {
    time: new Date(metrics.timestamp * 1000).toLocaleTimeString(),
    cpu: metrics.cpu.percent,
    memory: metrics.memory.percent,
    ...
  }])
}
```

#### Component Tree

```
App.jsx
├── BottleneckAlert      ← warning/critical banners at top
├── StatCard × 6         ← CPU, Memory, Swap, Disk, Load, IO Wait
├── MetricsChart         ← Recharts LineChart, 4 lines, 60 data points
├── CpuCoresChart        ← Recharts BarChart, one bar per CPU core
├── ProcessTable         ← top 10 processes by CPU, live
├── BenchmarkPanel       ← buttons → POST /api/benchmark/{type} → show result
└── ProfilerPanel        ← inputs + buttons → POST /api/profiler/* → show results
```

#### Why `isAnimationActive={false}` on charts?

Recharts animates chart updates by default. With data arriving every 2 seconds,
animations would constantly restart and the chart would flicker. Disabling animation
makes the live update smooth.

#### Benchmark flow from the UI side:

```
User clicks "CPU" button
  → BenchmarkPanel sets loading = 'cpu'
  → fetch POST /api/benchmark/cpu?threads=4&duration=10
  → waits (button shows spinner)
  → response arrives: { summary: "3241 events/sec, avg 1.23ms" }
  → result prepended to results list
  → loading = null, button re-enables
```

---

## 4. The Database — What Gets Stored

SQLite file: `backend/metrics.db`

Three tables:

**metric_snapshots** — one row every 5 seconds
```sql
id | timestamp           | cpu_percent | memory_percent | swap_percent | disk_percent | load_avg_1 | io_wait | ...
1  | 2024-05-14 11:00:00 | 23.4        | 61.2           | 0.0          | 54.3         | 1.2        | 3.2     | ...
2  | 2024-05-14 11:00:05 | 25.1        | 61.4           | 0.0          | 54.3         | 1.1        | 2.8     | ...
```

**benchmark_results** — one row per benchmark run
```sql
id | timestamp           | bench_type | tool     | duration_sec | summary                          | result_json
1  | 2024-05-14 11:05:00 | cpu        | sysbench | 10           | 3241.87 events/sec, avg 1.23ms   | {"events_per_second": 3241.87, ...}
```

**bottleneck_events** — one row per detected bottleneck
```sql
id | timestamp           | resource | severity | value | message
1  | 2024-05-14 11:10:00 | cpu      | warning  | 87.3  | CPU usage at 87.3% — warning saturation detected
```

You can inspect the database directly:
```bash
sqlite3 backend/metrics.db
.tables
SELECT * FROM metric_snapshots ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM bottleneck_events ORDER BY timestamp DESC LIMIT 10;
```

---

## 5. The sudo Setup — Why and How

`perf` reads CPU hardware counters. The Linux kernel restricts this to root
(or users with `CAP_PERFMON`) because hardware counters can be used to
extract information across process boundaries (a security concern).

We use the minimal privilege approach — only `perf` gets sudo, not the whole app:

```
/etc/sudoers entry:
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/perf
```

This means:
- `sudo perf record ...` works without a password prompt
- Everything else (psutil, sysbench, fio) runs as the normal user
- The FastAPI server itself runs as the normal user

This is exactly how production monitoring agents work — Datadog agent, Prometheus
node_exporter, etc. all use targeted privilege escalation for specific operations.

---

## 6. How to Explain This in an Interview

**"What does your project do?"**

> It's a real-time Linux performance monitoring and analysis dashboard. It collects
> CPU, memory, disk, and network metrics every 2 seconds using psutil and the /proc
> filesystem, streams them to a React frontend via WebSocket, automatically detects
> bottlenecks like CPU saturation or memory pressure, and lets you trigger benchmarks
> and generate CPU flame graphs directly from the UI.

**"Why WebSocket instead of polling?"**

> Polling would mean the frontend sends an HTTP request every 2 seconds. With WebSocket,
> the connection stays open and the server pushes data. It's lower latency, lower overhead
> (no HTTP headers on every update), and the server controls the cadence.

**"How does the FlameGraph work?"**

> We run `perf record` with `-F 99` to sample stack traces 99 times per second across
> all CPUs. Then `perf script` converts the binary data to text. We pipe that through
> Brendan Gregg's stackcollapse-perf.pl to aggregate identical stacks, then flamegraph.pl
> generates an SVG. The width of each block represents the proportion of CPU time spent
> in that function. The backend serves the SVG as a static file and the frontend embeds
> it in an iframe.

**"Why SQLite?"**

> This is a single-machine tool with a write rate of one row every 5 seconds. SQLite
> handles that easily and has zero operational overhead — no separate database process,
> no connection pooling, the file is right there and you can inspect it with any SQLite
> browser. If this were a multi-machine monitoring system, I'd switch to TimescaleDB
> or InfluxDB.

**"How does bottleneck detection work?"**

> The analyzer applies threshold rules to the raw metrics — for example, CPU above 85%
> is a warning, above 95% is critical. For load average, I normalize by CPU count so
> the threshold scales correctly regardless of how many cores the machine has. Each
> detected condition produces a structured object with resource, severity, value, and
> a human-readable message. These are both streamed live via WebSocket and persisted
> to SQLite for historical analysis.

**"Why FastAPI over Flask?"**

> FastAPI is async-native, which matters here because benchmark runs take 10–30 seconds.
> With async subprocesses, the server never blocks — other WebSocket clients keep
> receiving live metrics while a benchmark runs. Flask would require threading or
> a task queue like Celery to achieve the same thing. FastAPI also auto-generates
> Swagger docs from type annotations, which is useful for a project like this.

---

## 7. Full Request Lifecycle — Tracing One Benchmark Run

Here is every step that happens when you click "CPU" in the dashboard:

```
1. User clicks "CPU" button in BenchmarkPanel.jsx

2. Frontend:
   fetch("POST /api/benchmark/cpu?threads=4&duration=10")
   → button shows spinner, disabled

3. FastAPI router (benchmark.py):
   async def benchmark_cpu(threads=4, duration=10, db=...):
       result = await run_cpu_benchmark(threads=4, duration=10)

4. benchmark.py:
   cmd = ["sysbench", "cpu", "--threads=4", "--time=10", "run"]
   proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
   stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=40)
   # ← 10 seconds pass, sysbench runs, stdout captured

5. Parser extracts:
   { "events_per_second": 3241.87, "latency_avg_ms": 1.23, ... }

6. Result saved to SQLite:
   INSERT INTO benchmark_results (bench_type, tool, duration_sec, result_json, summary)
   VALUES ('cpu', 'sysbench', 10, '{"events_per_second": 3241.87}', '3241.87 events/sec...')

7. JSON response returned to frontend:
   { "tool": "sysbench", "type": "cpu", "summary": "3241.87 events/sec, avg latency 1.23ms", ... }

8. Frontend:
   setResults(prev => [{ ...res, id: Date.now() }, ...prev])
   setLoading(null)
   → result row appears, button re-enables

9. Meanwhile, throughout steps 4–8:
   The WebSocket loop kept running every 2 seconds
   Live metrics kept streaming to the browser
   (async never blocked the server)
```

---

## 8. File Map — Every File and Its Purpose

```
backend/app/
├── main.py               Entry point. Registers routes, starts background task,
│                         mounts static files, configures CORS.
│
├── core/database.py      SQLAlchemy async engine. Creates DB on startup.
│                         Provides get_db() dependency for route handlers.
│
├── models/metrics.py     Three SQLAlchemy ORM models:
│                         MetricSnapshot, BenchmarkResult, BottleneckEvent
│
├── collectors/system.py  All psutil calls + /proc/stat IO wait parser.
│                         collect_all() → single metrics dict.
│
├── services/
│   ├── analyzer.py       Threshold-based bottleneck detection.
│                         analyze(metrics) → list of bottleneck dicts.
│   │
│   ├── benchmark.py      Async subprocess wrappers for sysbench and fio.
│                         Parsers for their stdout output.
│   │
│   ├── profiler.py       perf record → perf script → stackcollapse → flamegraph pipeline.
│                         Saves SVG to flamegraphs/ directory.
│   │
│   └── collector_task.py Background asyncio task. Runs collect_all() + analyze()
│                         every 5s and writes to SQLite.
│
└── api/
    ├── ws.py             WebSocket /ws/metrics — pushes metrics every 2s.
    ├── metrics.py        REST: snapshot, history, bottleneck history.
    ├── benchmark.py      REST: trigger benchmarks, get history.
    └── profiler.py       REST: perf stat, flamegraph generation.

frontend/src/
├── App.jsx               Root layout. Assembles all components.
├── App.css               All styles (dark theme, responsive grid).
├── hooks/useMetrics.js   WebSocket hook. Manages connection, history array,
│                         auto-reconnect.
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
