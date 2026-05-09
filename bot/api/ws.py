from fastapi import APIRouter, WebSocket

from games.crash.engine import CrashEngine

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/crash")
async def crash_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    engine = CrashEngine()
    round_state = engine.seed_round()
    await websocket.send_json({"state": round_state.state, "multiplier": str(round_state.multiplier)})
