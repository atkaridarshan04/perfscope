import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.api import metrics, benchmark, profiler, ws
from app.services.collector_task import collect_and_store

FLAMEGRAPH_DIR = Path(__file__).parent.parent / "flamegraphs"


FLAMEGRAPH_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(collect_and_store())
    yield
    task.cancel()


app = FastAPI(
    title="Linux Performance Dashboard",
    description="Real-time Linux performance monitoring, benchmarking, and profiling.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router)
app.include_router(benchmark.router)
app.include_router(profiler.router)
app.include_router(ws.router)

# Serve generated flamegraph SVGs
app.mount("/flamegraphs", StaticFiles(directory=str(FLAMEGRAPH_DIR)), name="flamegraphs")


@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}
