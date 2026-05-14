"""
Bottleneck analyzer — converts raw metrics into actionable insights.

Thresholds based on industry-standard SRE practices:
  CPU    > 85% warning,  > 95% critical
  Memory > 80% warning,  > 95% critical
  Swap   > 20% warning,  > 60% critical
  Disk   > 80% warning,  > 95% critical
  Load   > cpu_count warning, > 2*cpu_count critical
  IOWait > 20% warning,  > 40% critical
"""

import psutil
from typing import List, Dict

CPU_WARN = 85.0
CPU_CRIT = 95.0
MEM_WARN = 80.0
MEM_CRIT = 95.0
SWAP_WARN = 20.0
SWAP_CRIT = 60.0
DISK_WARN = 80.0
DISK_CRIT = 95.0
IOWAIT_WARN = 20.0
IOWAIT_CRIT = 40.0


def _check(resource: str, value: float, warn: float, crit: float, unit: str, message_tpl: str) -> Dict | None:
    if value >= crit:
        return {"resource": resource, "severity": "critical", "value": value,
                "message": message_tpl.format(value=value, unit=unit, level="critical")}
    if value >= warn:
        return {"resource": resource, "severity": "warning", "value": value,
                "message": message_tpl.format(value=value, unit=unit, level="warning")}
    return None


def analyze(metrics: dict) -> List[Dict]:
    bottlenecks = []
    cpu_count = psutil.cpu_count(logical=True) or 1

    # CPU
    b = _check("cpu", metrics["cpu"]["percent"], CPU_WARN, CPU_CRIT, "%",
               "CPU usage at {value}{unit} — {level} saturation detected")
    if b: bottlenecks.append(b)

    # Memory
    b = _check("memory", metrics["memory"]["percent"], MEM_WARN, MEM_CRIT, "%",
               "Memory usage at {value}{unit} — {level} memory pressure")
    if b: bottlenecks.append(b)

    # Swap
    b = _check("swap", metrics["memory"]["swap_percent"], SWAP_WARN, SWAP_CRIT, "%",
               "Swap usage at {value}{unit} — system is paging ({level})")
    if b: bottlenecks.append(b)

    # Disk
    b = _check("disk", metrics["disk"]["percent"], DISK_WARN, DISK_CRIT, "%",
               "Disk usage at {value}{unit} — {level}: filesystem filling up")
    if b: bottlenecks.append(b)

    # Load average (normalized by CPU count)
    load1 = metrics["load"]["avg_1"]
    load_norm = (load1 / cpu_count) * 100
    if load_norm >= 200:
        bottlenecks.append({"resource": "load", "severity": "critical", "value": load1,
                             "message": f"Load average {load1} on {cpu_count} CPUs — critical overload"})
    elif load_norm >= 100:
        bottlenecks.append({"resource": "load", "severity": "warning", "value": load1,
                             "message": f"Load average {load1} on {cpu_count} CPUs — system overloaded"})

    # IO Wait
    if metrics.get("io_wait") is not None:
        b = _check("iowait", metrics["io_wait"], IOWAIT_WARN, IOWAIT_CRIT, "%",
                   "IO wait at {value}{unit} — {level} disk bottleneck")
        if b: bottlenecks.append(b)

    return bottlenecks
