from fastapi import APIRouter
from app.services.profiler import run_perf_stat, generate_flamegraph

router = APIRouter(prefix="/api/profiler", tags=["profiler"])


@router.post("/perf-stat")
async def perf_stat(pid: int | None = None, duration: int = 5):
    """Run perf stat and return hardware counter data."""
    return await run_perf_stat(pid=pid, duration=duration)


@router.post("/flamegraph")
async def flamegraph(pid: int | None = None, duration: int = 10):
    """Generate a FlameGraph SVG. Returns URL to the SVG."""
    return await generate_flamegraph(pid=pid, duration=duration)
