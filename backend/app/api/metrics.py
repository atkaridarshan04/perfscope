from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.metrics import MetricSnapshot, BottleneckEvent
from app.collectors.system import collect_all
from app.services.analyzer import analyze

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/snapshot")
async def get_snapshot():
    """Single real-time snapshot."""
    metrics = collect_all()
    bottlenecks = analyze(metrics)
    return {"metrics": metrics, "bottlenecks": bottlenecks}


@router.get("/history")
async def get_history(limit: int = 60, db: AsyncSession = Depends(get_db)):
    """Last N metric snapshots from DB."""
    result = await db.execute(
        select(MetricSnapshot).order_by(desc(MetricSnapshot.timestamp)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "timestamp": r.timestamp,
            "cpu_percent": r.cpu_percent,
            "memory_percent": r.memory_percent,
            "swap_percent": r.swap_percent,
            "disk_percent": r.disk_percent,
            "load_avg_1": r.load_avg_1,
            "io_wait": r.io_wait,
        }
        for r in reversed(rows)
    ]


@router.get("/bottlenecks")
async def get_bottleneck_history(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BottleneckEvent).order_by(desc(BottleneckEvent.timestamp)).limit(limit)
    )
    rows = result.scalars().all()
    return [{"timestamp": r.timestamp, "resource": r.resource,
             "severity": r.severity, "message": r.message, "value": r.value}
            for r in rows]
