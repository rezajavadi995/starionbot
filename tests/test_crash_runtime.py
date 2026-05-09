import asyncio

from bot.services.crash_runtime import CrashRuntime


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict[str, object]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict[str, object]) -> None:
        self.messages.append(payload)


def test_crash_runtime_broadcasts_round_events() -> None:
    asyncio.run(_scenario())


async def _scenario() -> None:
    runtime = CrashRuntime(tick_seconds=0.01, wait_seconds=0.01)
    ws = FakeWebSocket()

    await runtime.start()
    await runtime.connect(ws)  # type: ignore[arg-type]
    await asyncio.sleep(0.08)
    await runtime.disconnect(ws)  # type: ignore[arg-type]
    await runtime.stop()

    event_types = [m.get("type") for m in ws.messages]
    assert "history" in event_types
    assert "round_waiting" in event_types
    assert "round_started" in event_types
    assert "round_update" in event_types
