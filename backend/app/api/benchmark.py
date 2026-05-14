import json
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.metrics import BenchmarkResult
from app.services.benchmark import run_cpu_benchmark, run_memory_benchmark, run_disk_benchmark

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


async def _save_result(db: AsyncSession, result: dict):
    row = BenchmarkResult(
        bench_type=result.get("type", "unknown"),
        tool=result.get("tool", "unknown"),
        duration_sec=result.get("duration_sec", 0),
        result_json=json.dumps(result.get("results", {})),
        summary=result.get("summary", ""),
    )
    db.add(row)
    await db.commit()


@router.post("/cpu")
async def benchmark_cpu(threads: int = 4, duration: int = 10, db: AsyncSession = Depends(get_db)):
    result = await run_cpu_benchmark(threads=threads, duration=duration)
    if "error" not in result:
        await _save_result(db, result)
    return result


@router.post("/memory")
async def benchmark_memory(duration: int = 10, db: AsyncSession = Depends(get_db)):
    result = await run_memory_benchmark(duration=duration)
    if "error" not in result:
        await _save_result(db, result)
    return result


@router.post("/disk")
async def benchmark_disk(duration: int = 10, db: AsyncSession = Depends(get_db)):
    result = await run_disk_benchmark(duration=duration)
    if "error" not in result:
        await _save_result(db, result)
    return result


@router.get("/history")
async def benchmark_history(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BenchmarkResult).order_by(desc(BenchmarkResult.timestamp)).limit(limit)
    )
    rows = result.scalars().all()
    return [{"id": r.id, "timestamp": r.timestamp, "type": r.bench_type,
             "tool": r.tool, "summary": r.summary, "results": json.loads(r.result_json)}
            for r in rows]
