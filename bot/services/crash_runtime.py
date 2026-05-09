import asyncio
from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import WebSocket

from games.crash.engine import CrashEngine, CrashRound, RoundState


class CrashRuntime:
    """Realtime crash round loop with websocket fan-out and short in-memory history."""

    def __init__(self, *, tick_seconds: float = 0.35, wait_seconds: float = 3.0) -> None:
        self._engine = CrashEngine()
        self._tick_seconds = tick_seconds
        self._wait_seconds = wait_seconds
        self._clients: set[WebSocket] = set()
        self._history: deque[dict[str, Any]] = deque(maxlen=30)
        self._round: CrashRound | None = None
        self._round_id = 0
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        await websocket.send_json({"type": "history", "rounds": list(self._history)})
        current = self._round
        if current is not None:
            await websocket.send_json(self._event_payload("round_update", current))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    def _event_payload(self, event_type: str, round_state: CrashRound) -> dict[str, Any]:
        return {
            "type": event_type,
            "round_id": self._round_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "state": round_state.state,
            "multiplier": f"{round_state.multiplier:.2f}",
        }

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        disconnected: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                disconnected.append(client)
        if disconnected:
            async with self._lock:
                for client in disconnected:
                    self._clients.discard(client)

    async def _run_loop(self) -> None:
        while True:
            self._round_id += 1
            seeded = self._engine.seed_round()
            self._round = seeded
            await self._broadcast(self._event_payload("round_waiting", seeded))
            await asyncio.sleep(self._wait_seconds)

            round_state = CrashRound(
                state=RoundState.ACTIVE,
                multiplier=Decimal("1.00"),
                crash_point=seeded.crash_point,
            )
            self._round = round_state
            await self._broadcast(self._event_payload("round_started", round_state))

            while round_state.state != RoundState.CRASHED:
                await asyncio.sleep(self._tick_seconds)
                round_state = self._engine.step(round_state)
                self._round = round_state
                await self._broadcast(self._event_payload("round_update", round_state))

            crashed_record = {
                "round_id": self._round_id,
                "crash_multiplier": f"{round_state.multiplier:.2f}",
                "state": round_state.state,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self._history.appendleft(crashed_record)
            await self._broadcast({"type": "round_crashed", **crashed_record})
