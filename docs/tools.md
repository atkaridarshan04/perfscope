# Tool Reference

## psutil

Python library that abstracts Linux's `/proc` filesystem into a clean API.

| Function | What it reads | Returns |
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

Linux exposes kernel internals as virtual files:

```
/proc/stat        — CPU time counters (user, nice, system, idle, iowait...)
/proc/meminfo     — Memory and swap details
/proc/loadavg     — Load averages + running/total processes
/proc/<pid>/stat  — Per-process CPU/memory stats
/proc/diskstats   — Block device IO counters
/proc/net/dev     — Network interface counters
```

IO wait is calculated from `/proc/stat`:
```
iowait% = (iowait_ticks / total_ticks) * 100
```

---

## perf

Linux kernel performance counters tool. Reads CPU hardware performance monitoring units (PMUs).

### perf stat
Counts hardware events over a time window:
```bash
sudo perf stat -e cycles,instructions,cache-misses,branch-misses -- sleep 5
```

Key metrics:
| Counter | Meaning | High value means |
|---|---|---|
| cycles | CPU clock cycles consumed | High CPU usage |
| instructions | Instructions executed | Workload size |
| cache-misses | L1/L2/L3 cache misses | Memory inefficiency |
| branch-misses | Mispredicted branches | Poor branch patterns |
| IPC (inst/cycle) | Instructions per cycle | CPU efficiency |

### perf record + FlameGraph
```bash
sudo perf record -F 99 -g -a -- sleep 10   # sample at 99Hz, all CPUs
sudo perf script | stackcollapse-perf.pl | flamegraph.pl > out.svg
```

`-F 99` — sample at 99Hz (not 100Hz to avoid lockstep with timer interrupts)
`-g` — capture call graphs (stack traces)
`-a` — system-wide (all CPUs)
`-p <pid>` — profile specific process only

---

## sysbench

Benchmark tool for CPU and memory.

### CPU benchmark
```bash
sysbench cpu --threads=4 --time=10 run
```
Computes prime numbers. Measures:
- Events per second (higher = faster CPU)
- Latency (min/avg/max ms per event)

### Memory benchmark
```bash
sysbench memory --time=10 run
```
Sequential memory read/write. Measures:
- Throughput in MiB/sec

---

## fio

Flexible IO tester. Used for disk benchmarks.

```bash
fio --name=test --ioengine=libaio --iodepth=16 \
    --rw=randrw --bs=4k --direct=1 --size=128m \
    --runtime=10 --time_based --output-format=json
```

Key parameters:
| Param | Meaning |
|---|---|
| `ioengine=libaio` | Linux async IO (most realistic) |
| `iodepth=16` | 16 concurrent IO requests |
| `rw=randrw` | Mixed random read+write |
| `bs=4k` | 4KB block size (typical for databases) |
| `direct=1` | Bypass page cache (raw disk speed) |

Key output metrics:
| Metric | Meaning |
|---|---|
| `bw` | Bandwidth in KB/s |
| `iops` | IO operations per second |
| `lat_ns.mean` | Average latency in nanoseconds |

---

## FlameGraph (Brendan Gregg)

Visualizes where CPU time is spent across the call stack.

```
Wide block  → function consumes more CPU time
Tall stack  → deep call chain
```

Reading a flame graph:
- X-axis = alphabetical (NOT time order)
- Y-axis = call stack depth
- Width = proportion of CPU samples
- Look for the widest blocks at the top — those are your hotspots

Repository: https://github.com/brendangregg/FlameGraph
