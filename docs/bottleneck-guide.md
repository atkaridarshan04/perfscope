# Bottleneck Detection Guide

The analyzer (`backend/app/services/analyzer.py`) converts raw metrics into actionable alerts. Each detected condition produces a structured object with `resource`, `severity`, `value`, and a human-readable `message`.

---

## Thresholds

| Resource | Warning | Critical |
|---|---|---|
| CPU | > 85% | > 95% |
| Memory | > 80% | > 95% |
| Swap | > 20% | > 60% |
| Disk space | > 80% | > 95% |
| Load average | > 1× CPU count | > 2× CPU count |
| IO Wait | > 20% | > 40% |

---

## CPU Bottleneck

**Alert:** `CPU usage at 92% — critical saturation detected`

The CPU is nearly fully utilized. New work queues waiting for CPU time.

**Common causes:** too many concurrent processes, inefficient algorithms, runaway process.

**Investigate:**
1. Check the Process Table — which process has the highest CPU%?
2. Run `perf stat` on that PID to check instruction efficiency (IPC)
3. Generate a FlameGraph to find the hot function

---

## Memory Pressure

**Alert:** `Memory usage at 88% — warning: memory pressure`

Available RAM is low. The kernel may start swapping soon.

**Common causes:** memory leak, too many processes, large dataset in RAM.

**Investigate:** Check Process Table for highest Mem%. Watch if Swap% starts rising.

---

## Swap Activity

**Alert:** `Swap usage at 35% — system is paging (warning)`

The system is using disk as overflow RAM. Disk is 100–1000× slower than RAM — even 20% swap causes noticeable slowdowns.

**Common causes:** RAM exhausted, memory leak, too many services.

---

## IO Wait

**Alert:** `IO wait at 35% — warning: disk bottleneck`

CPUs are idle waiting for disk IO to complete. The disk is the bottleneck, not the CPU.

**Common causes:** slow HDD, disk saturated with writes, heavy database scans.

**Investigate:**
1. Run the Disk benchmark to measure raw disk speed
2. Check `disk_read_mb` / `disk_write_mb` in metrics to see which direction is heavy

---

## High Load Average

**Alert:** `Load average 8.2 on 4 CPUs — system overloaded`

Load average counts processes in R (running) or D (uninterruptible sleep / IO wait) state. On a 4-core machine, load = 4.0 means 100% utilized; load = 8.0 means processes are queuing.

The analyzer normalizes: `load_norm = (load_1min / cpu_count) * 100`.

Load average alone doesn't tell you *why* — check IO Wait and CPU% together to distinguish CPU-bound from IO-bound overload.

---

## Disk Space

**Alert:** `Disk usage at 91% — critical: filesystem filling up`

At 100%, writes fail and applications crash. Find large files immediately:

```bash
du -sh /* 2>/dev/null | sort -rh | head -20
```
