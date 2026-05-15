"""
Background task: collect metrics every 5 seconds and persist to SQLite.
Also persists bottleneck events when detected.
"""

import asyncio
from app.collectors.system import collect_all
from app.services.analyzer import analyze
from app.core.database import SessionLocal
from app.models.metrics import MetricSnapshot, BottleneckEvent


async def collect_and_store():
    while True:
        try:
            metrics = await collect_all()
            bottlenecks = analyze(metrics)

            async with SessionLocal() as db:
                snapshot = MetricSnapshot(
                    cpu_percent=metrics["cpu"]["percent"],
                    cpu_freq_mhz=metrics["cpu"]["freq_mhz"],
                    memory_percent=metrics["memory"]["percent"],
                    memory_used_gb=metrics["memory"]["used_gb"],
                    memory_available_gb=metrics["memory"]["available_gb"],
                    swap_percent=metrics["memory"]["swap_percent"],
                    swap_used_gb=metrics["memory"]["swap_used_gb"],
                    disk_read_mb=metrics["disk"]["read_mb"],
                    disk_write_mb=metrics["disk"]["write_mb"],
                    disk_percent=metrics["disk"]["percent"],
                    net_sent_mb=metrics["network"]["sent_mb"],
                    net_recv_mb=metrics["network"]["recv_mb"],
                    load_avg_1=metrics["load"]["avg_1"],
                    load_avg_5=metrics["load"]["avg_5"],
                    load_avg_15=metrics["load"]["avg_15"],
                    io_wait=metrics.get("io_wait"),
                )
                db.add(snapshot)

                for b in bottlenecks:
                    db.add(BottleneckEvent(
                        resource=b["resource"],
                        severity=b["severity"],
                        message=b["message"],
                        value=b["value"],
                    ))

                await db.commit()
        except Exception as e:
            print(f"[collector] error: {e}")

        await asyncio.sleep(5)
