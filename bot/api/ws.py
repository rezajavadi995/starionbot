from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bot.services.crash_runtime import CrashRuntime

router = APIRouter(prefix="/ws", tags=["ws"])
crash_runtime = CrashRuntime()


@router.websocket("/crash")
async def crash_updates(websocket: WebSocket) -> None:
    await crash_runtime.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await crash_runtime.disconnect(websocket)
