# Bottleneck Detection Guide

The analyzer (`backend/app/services/analyzer.py`) automatically converts raw metrics into actionable insights. Here's how to interpret each alert.

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

**What it means:** The CPU is nearly fully utilized. New requests queue up waiting for CPU time.

**Common causes:**
- Too many concurrent processes
- Inefficient algorithms (O(n²) loops, etc.)
- Missing parallelism
- Runaway process

**How to investigate:**
1. Check the Process Table — which process has highest CPU%?
2. Run `perf stat` on that PID to see instruction efficiency
3. Generate a FlameGraph to find the hot function

---

## Memory Pressure

**Alert:** `Memory usage at 88% — warning: memory pressure`

**What it means:** Available RAM is low. The kernel may start swapping soon.

**Common causes:**
- Memory leak in application
- Too many processes
- Large dataset loaded into RAM

**How to investigate:**
1. Check Process Table — which process has highest Mem%?
2. Watch if Swap% starts rising (confirms pressure)

---

## Swap Activity

**Alert:** `Swap usage at 35% — system is paging (warning)`

**What it means:** The system is using disk as overflow RAM. Disk is 100–1000× slower than RAM. This causes severe performance degradation.

**Common causes:**
- RAM exhausted
- Memory leak
- Too many services running

**This is serious.** Even 20% swap can cause noticeable slowdowns because every swap access hits disk.

---

## IO Wait

**Alert:** `IO wait at 35% — warning: disk bottleneck`

**What it means:** CPUs are idle waiting for disk IO to complete. The disk is the bottleneck, not the CPU.

**Common causes:**
- Slow HDD (vs SSD)
- Disk saturated with writes
- Database doing heavy sequential scans
- RAID rebuild in progress

**How to investigate:**
1. Run the Disk benchmark to measure raw disk speed
2. Check `disk_read_mb` and `disk_write_mb` in the metrics — which direction is heavy?

---

## High Load Average

**Alert:** `Load average 8.2 on 4 CPUs — system overloaded`

**What it means:** Load average counts processes in R (running) or D (uninterruptible sleep, usually IO wait) state. A load of 4.0 on a 4-core system = 100% utilized.

**Load > CPU count** = processes are queuing, waiting for CPU or IO.

**Note:** Load average alone doesn't tell you *why* — it could be CPU-bound or IO-bound. Check IO Wait and CPU% together.

---

## Disk Space

**Alert:** `Disk usage at 91% — critical: filesystem filling up`

**What it means:** The filesystem is nearly full. At 100%, writes fail, applications crash, logs stop.

**Immediate action:** Find and remove large files.
```bash
du -sh /* 2>/dev/null | sort -rh | head -20
```
