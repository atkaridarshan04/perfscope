"""
Benchmark runner — wraps sysbench, fio, stress-ng.
Each function runs the tool as a subprocess and returns parsed results.
"""

import asyncio
import json
import re
import shutil
from typing import Optional


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


async def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "timeout"


def _parse_sysbench_cpu(output: str) -> dict:
    result = {}
    for line in output.splitlines():
        if "events per second" in line:
            result["events_per_second"] = float(re.search(r"[\d.]+", line).group())
        if "total time" in line:
            result["total_time_sec"] = float(re.search(r"[\d.]+", line).group())
        if "min:" in line:
            result["latency_min_ms"] = float(re.search(r"[\d.]+", line).group())
        if "avg:" in line:
            result["latency_avg_ms"] = float(re.search(r"[\d.]+", line).group())
        if "max:" in line:
            result["latency_max_ms"] = float(re.search(r"[\d.]+", line).group())
    return result


def _parse_sysbench_memory(output: str) -> dict:
    result = {}
    for line in output.splitlines():
        if "transferred" in line:
            m = re.search(r"([\d.]+)\s*MiB/sec", line)
            if m:
                result["throughput_mib_sec"] = float(m.group(1))
        if "total time" in line:
            result["total_time_sec"] = float(re.search(r"[\d.]+", line).group())
    return result


def _parse_fio(output: str) -> dict:
    try:
        data = json.loads(output)
        job = data["jobs"][0]
        return {
            "read_bw_kb": job["read"]["bw"],
            "read_iops": job["read"]["iops"],
            "read_lat_ms": round(job["read"]["lat_ns"]["mean"] / 1e6, 3),
            "write_bw_kb": job["write"]["bw"],
            "write_iops": job["write"]["iops"],
            "write_lat_ms": round(job["write"]["lat_ns"]["mean"] / 1e6, 3),
        }
    except Exception:
        return {"raw": output[:500]}


async def run_cpu_benchmark(threads: int = 4, duration: int = 10) -> dict:
    if not _tool_available("sysbench"):
        return {"error": "sysbench not installed. Run: sudo apt install sysbench"}
    cmd = ["sysbench", "cpu", f"--threads={threads}", f"--time={duration}", "run"]
    rc, out, err = await _run(cmd, timeout=duration + 30)
    if rc != 0:
        return {"error": err or "sysbench failed"}
    parsed = _parse_sysbench_cpu(out)
    return {
        "tool": "sysbench",
        "type": "cpu",
        "threads": threads,
        "duration_sec": duration,
        "results": parsed,
        "summary": f"{parsed.get('events_per_second', '?')} events/sec, avg latency {parsed.get('latency_avg_ms', '?')}ms",
    }


async def run_memory_benchmark(duration: int = 10) -> dict:
    if not _tool_available("sysbench"):
        return {"error": "sysbench not installed. Run: sudo apt install sysbench"}
    cmd = ["sysbench", "memory", f"--time={duration}", "run"]
    rc, out, err = await _run(cmd, timeout=duration + 30)
    if rc != 0:
        return {"error": err or "sysbench failed"}
    parsed = _parse_sysbench_memory(out)
    return {
        "tool": "sysbench",
        "type": "memory",
        "duration_sec": duration,
        "results": parsed,
        "summary": f"{parsed.get('throughput_mib_sec', '?')} MiB/sec",
    }


async def run_disk_benchmark(duration: int = 10, path: str = "/tmp/fio_test") -> dict:
    if not _tool_available("fio"):
        return {"error": "fio not installed. Run: sudo apt install fio"}
    cmd = [
        "fio", "--name=randreadwrite", "--ioengine=libaio", "--iodepth=16",
        "--rw=randrw", "--bs=4k", "--direct=1", f"--size=128m",
        f"--runtime={duration}", "--time_based", f"--filename={path}",
        "--output-format=json",
    ]
    rc, out, err = await _run(cmd, timeout=duration + 60)
    # cleanup test file
    import os
    try: os.remove(path)
    except: pass
    if rc != 0:
        return {"error": err or "fio failed"}
    parsed = _parse_fio(out)
    return {
        "tool": "fio",
        "type": "disk",
        "duration_sec": duration,
        "results": parsed,
        "summary": f"Read {parsed.get('read_bw_kb', '?')} KB/s | Write {parsed.get('write_bw_kb', '?')} KB/s",
    }
