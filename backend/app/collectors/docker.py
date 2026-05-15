"""
Docker container metrics collector.

Reads from the Docker socket (/var/run/docker.sock) using the Docker HTTP API.
Returns an empty list if Docker is not available (non-Docker environments).
"""

import asyncio
import json
import os
from typing import Optional


_SOCKET = "/var/run/docker.sock"


def _docker_available() -> bool:
    return os.path.exists(_SOCKET)


async def _docker_get(path: str) -> Optional[dict | list]:
    """Make a GET request to the Docker Unix socket API."""
    try:
        reader, writer = await asyncio.open_unix_connection(_SOCKET)
        request = f"GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        writer.write(request.encode())
        await writer.drain()
        raw = await reader.read(1 << 20)  # 1MB max
        writer.close()
        # Split HTTP headers from body
        _, _, body = raw.decode(errors="replace").partition("\r\n\r\n")
        # Handle chunked transfer encoding (strip chunk sizes)
        if "\r\n" in body[:10]:
            lines = body.split("\r\n")
            body = "".join(l for l in lines if not all(c in "0123456789abcdefABCDEF" for c in l.strip()) and l)
        return json.loads(body)
    except Exception:
        return None


async def get_container_metrics() -> list[dict]:
    """
    Returns a list of running containers with their CPU and memory stats.
    Each entry: { id, name, image, status, cpu_percent, mem_usage_mb, mem_limit_mb, mem_percent }
    """
    if not _docker_available():
        return []

    containers = await _docker_get("/containers/json")
    if not containers:
        return []

    results = []
    for c in containers:
        cid = c.get("Id", "")[:12]
        name = (c.get("Names") or ["unknown"])[0].lstrip("/")
        image = c.get("Image", "unknown")
        status = c.get("Status", "unknown")

        stats = await _docker_get(f"/containers/{cid}/stats?stream=false")
        if not stats:
            continue

        cpu_percent = _calc_cpu_percent(stats)
        mem = stats.get("memory_stats", {})
        mem_usage = mem.get("usage", 0)
        mem_limit = mem.get("limit", 1)
        # Subtract cache from usage (matches `docker stats` display)
        cache = mem.get("stats", {}).get("cache", 0)
        mem_usage = max(0, mem_usage - cache)

        results.append({
            "id": cid,
            "name": name,
            "image": image,
            "status": status,
            "cpu_percent": round(cpu_percent, 2),
            "mem_usage_mb": round(mem_usage / 1e6, 1),
            "mem_limit_mb": round(mem_limit / 1e6, 1),
            "mem_percent": round((mem_usage / mem_limit) * 100, 1) if mem_limit else 0.0,
        })

    return results


def _calc_cpu_percent(stats: dict) -> float:
    """Calculate CPU % the same way `docker stats` does."""
    try:
        cpu = stats["cpu_stats"]
        precpu = stats["precpu_stats"]
        cpu_delta = cpu["cpu_usage"]["total_usage"] - precpu["cpu_usage"]["total_usage"]
        sys_delta = cpu["system_cpu_usage"] - precpu["system_cpu_usage"]
        num_cpus = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage", [1]))
        if sys_delta > 0 and cpu_delta > 0:
            return (cpu_delta / sys_delta) * num_cpus * 100.0
    except (KeyError, ZeroDivisionError):
        pass
    return 0.0
