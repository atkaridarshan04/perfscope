import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.collectors.system import collect_all
from app.services.analyzer import analyze

router = APIRouter()

# Active WebSocket connections
_connections: list[WebSocket] = []


@router.websocket("/ws/metrics")
async def metrics_ws(websocket: WebSocket):
    await websocket.accept()
    _connections.append(websocket)
    try:
        while True:
            metrics = await collect_all()
            bottlenecks = analyze(metrics)
            await websocket.send_text(json.dumps({
                "metrics": metrics,
                "bottlenecks": bottlenecks,
            }))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        _connections.remove(websocket)
    except Exception:
        if websocket in _connections:
            _connections.remove(websocket)
