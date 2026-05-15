# Tool Reference

## psutil

Python library that abstracts Linux's `/proc` filesystem into a clean API. Used in `collectors/system.py` for all metric collection.

| Function | Reads from | Returns |
|---|---|---|
| `cpu_percent()` | `/proc/stat` | Overall CPU % |
| `cpu_percent(percpu=True)` | `/proc/stat` | Per-core list |
| `cpu_freq()` | `/sys/devices/system/cpu/` | Current MHz |
| `virtual_memory()` | `/proc/meminfo` | RAM stats |
| `swap_memory()` | `/proc/meminfo` | Swap stats |
| `disk_usage(path)` | `statvfs()` syscall | Disk space |
| `disk_io_counters()` | `/proc/diskstats` | Read/write bytes |
| `net_io_counters()` | `/proc/net/dev` | Network bytes |
| `process_iter()` | `/proc/<pid>/stat` | All processes |
| `getloadavg()` | `/proc/loadavg` | 1/5/15 min load |

---

## /proc filesystem

Linux exposes kernel internals as virtual files generated on-the-fly:

```
/proc/stat        — CPU time counters (user, nice, system, idle, iowait, irq, softirq...)
/proc/meminfo     — Memory and swap details
/proc/loadavg     — Load averages + running/total process counts
/proc/<pid>/stat  — Per-process CPU/memory stats
/proc/diskstats   — Block device IO counters
/proc/net/dev     — Network interface counters
```

IO wait is calculated directly from `/proc/stat`:
```python
iowait% = (iowait_ticks / total_ticks) * 100
```

---

## perf

Linux kernel performance counters tool. Reads CPU hardware Performance Monitoring Units (PMUs) — physical registers in the CPU silicon.

### perf stat

Counts hardware events over a time window:
```bash
sudo perf stat -e cycles,instructions,cache-misses,branch-misses -- sleep 5
```

| Counter | Meaning | High value indicates |
|---|---|---|
| `cycles` | CPU clock cycles consumed | High CPU usage |
| `instructions` | Instructions executed | Workload size |
| `cache-misses` | L1/L2/L3 cache misses | Memory access inefficiency |
| `branch-misses` | Mispredicted branches | Poor branch patterns |
| IPC (`instructions/cycles`) | Instructions per cycle | CPU efficiency (< 1.0 = stalling) |

### perf record + FlameGraph pipeline

```bash
# Step 1: Record stack traces at 99Hz for 10s (system-wide)
sudo perf record -F 99 -g -a -o /tmp/perf.data -- sleep 10

# Step 2: Convert binary to text
sudo perf script -i /tmp/perf.data > perf_output.txt

# Step 3: Collapse identical stacks
perl /opt/FlameGraph/stackcollapse-perf.pl < perf_output.txt > collapsed.txt

# Step 4: Generate SVG
perl /opt/FlameGraph/flamegraph.pl < collapsed.txt > flamegraph.svg
```

Flag notes:
- `-F 99` — 99Hz, not 100Hz, to avoid lockstep with timer interrupts
- `-g` — capture full call graphs (stack traces, not just top-level function)
- `-a` — system-wide across all CPUs; use `-p <pid>` for a specific process

---

## sysbench

Benchmark tool for CPU and memory.

### CPU benchmark
```bash
sysbench cpu --threads=4 --time=10 run
```
Computes prime numbers up to 10,000 repeatedly. Pure CPU workload — no disk, no network.

Key output: `events_per_second`, `latency_avg_ms`

### Memory benchmark
```bash
sysbench memory --time=10 run
```
Sequential memory read/write. Key output: throughput in MiB/sec.

---

## fio

Flexible IO tester for disk benchmarks.

```bash
fio --name=randreadwrite --ioengine=libaio --iodepth=16 \
    --rw=randrw --bs=4k --direct=1 --size=128m \
    --runtime=10 --time_based \
    --filename=/tmp/fio_test --output-format=json
```

| Parameter | Meaning |
|---|---|
| `ioengine=libaio` | Linux async IO — most realistic for production workloads |
| `iodepth=16` | 16 concurrent IO requests in flight (simulates a busy database) |
| `rw=randrw` | Mixed random reads and writes (worst case for spinning disks) |
| `bs=4k` | 4KB block size (standard database page size) |
| `direct=1` | Bypass OS page cache — measures actual disk speed |

Key output metrics: `read_bw_kb`, `read_iops`, `read_lat_ms`, `write_bw_kb`, `write_iops`, `write_lat_ms`

---

## FlameGraph (Brendan Gregg)

Visualizes where CPU time is spent across the call stack.

- **X-axis** — alphabetical order (not time)
- **Y-axis** — call stack depth
- **Block width** — proportion of CPU samples in that function
- **Wide blocks at the top** — your hotspots

The SVG is interactive: click any block to zoom into that subtree.

Repository: https://github.com/brendangregg/FlameGraph
