"""
perf + FlameGraph integration.

Flow:
  1. Run `sudo perf record -g -p <pid> -- sleep <duration>`  (or system-wide)
  2. Run `sudo perf script` to dump raw stacks
  3. Pipe through stackcollapse-perf.pl → flamegraph.pl
  4. Save SVG to flamegraphs/ directory
  5. Return path for frontend to embed

Requires:
  - perf installed: sudo apt install linux-perf
  - FlameGraph scripts cloned to /opt/FlameGraph
  - sudoers entry: <user> ALL=(ALL) NOPASSWD: /usr/bin/perf
"""

import asyncio
import os
import time
from pathlib import Path

FLAMEGRAPH_DIR = Path(__file__).parent.parent.parent.parent / "flamegraphs"
FLAMEGRAPH_SCRIPTS = Path("/opt/FlameGraph")
PERF_DATA = "/tmp/perf.data"


async def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "timeout"


def _scripts_available() -> bool:
    return (FLAMEGRAPH_SCRIPTS / "stackcollapse-perf.pl").exists() and \
           (FLAMEGRAPH_SCRIPTS / "flamegraph.pl").exists()


async def run_perf_stat(pid: int | None = None, duration: int = 5) -> dict:
    """Run perf stat and return hardware counter summary."""
    cmd = ["sudo", "perf", "stat", "-e",
           "cycles,instructions,cache-misses,cache-references,branch-misses,branches",
           "--", "sleep", str(duration)]
    if pid:
        cmd = ["sudo", "perf", "stat", "-e",
               "cycles,instructions,cache-misses,cache-references,branch-misses,branches",
               "-p", str(pid), "--", "sleep", str(duration)]

    rc, out, err = await _run(cmd, timeout=duration + 15)
    # perf stat writes to stderr
    raw = err if err else out
    return {"raw": raw, "parsed": _parse_perf_stat(raw)}


def _parse_perf_stat(output: str) -> dict:
    result = {}
    patterns = {
        "cycles": r"([\d,]+)\s+cycles",
        "instructions": r"([\d,]+)\s+instructions",
        "cache_misses": r"([\d,]+)\s+cache-misses",
        "cache_references": r"([\d,]+)\s+cache-references",
        "branch_misses": r"([\d,]+)\s+branch-misses",
        "branches": r"([\d,]+)\s+branches",
    }
    import re
    for key, pattern in patterns.items():
        m = re.search(pattern, output)
        if m:
            result[key] = int(m.group(1).replace(",", ""))
    return result


async def generate_flamegraph(pid: int | None = None, duration: int = 10) -> dict:
    """
    Record perf data and generate a FlameGraph SVG.
    Returns {"svg_path": "...", "svg_url": "/flamegraphs/..."} or {"error": "..."}
    """
    if not _scripts_available():
        return {
            "error": "FlameGraph scripts not found at /opt/FlameGraph. "
                     "Run: sudo git clone https://github.com/brendangregg/FlameGraph /opt/FlameGraph"
        }

    FLAMEGRAPH_DIR.mkdir(exist_ok=True)
    svg_name = f"flamegraph_{int(time.time())}.svg"
    svg_path = FLAMEGRAPH_DIR / svg_name

    # Step 1: perf record
    if pid:
        record_cmd = ["sudo", "perf", "record", "-F", "99", "-g", "-p", str(pid),
                      "-o", PERF_DATA, "--", "sleep", str(duration)]
    else:
        record_cmd = ["sudo", "perf", "record", "-F", "99", "-g", "-a",
                      "-o", PERF_DATA, "--", "sleep", str(duration)]

    rc, _, err = await _run(record_cmd, timeout=duration + 20)
    if rc != 0:
        return {"error": f"perf record failed: {err}"}

    # Step 2: perf script
    rc, script_out, err = await _run(["sudo", "perf", "script", "-i", PERF_DATA],
                                      timeout=30)
    if rc != 0:
        return {"error": f"perf script failed: {err}"}

    # Step 3: stackcollapse | flamegraph
    collapse = await asyncio.create_subprocess_exec(
        "perl", str(FLAMEGRAPH_SCRIPTS / "stackcollapse-perf.pl"),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    collapsed, _ = await collapse.communicate(input=script_out.encode())

    flame = await asyncio.create_subprocess_exec(
        "perl", str(FLAMEGRAPH_SCRIPTS / "flamegraph.pl"),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    svg_bytes, _ = await flame.communicate(input=collapsed)

    svg_path.write_bytes(svg_bytes)

    # cleanup
    try:
        os.remove(PERF_DATA)
    except Exception:
        pass

    return {"svg_path": str(svg_path), "svg_url": f"/flamegraphs/{svg_name}"}
