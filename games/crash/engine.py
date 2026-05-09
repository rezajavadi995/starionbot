from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import random


class RoundState(StrEnum):
    WAITING = "waiting"
    ACTIVE = "active"
    CRASHED = "crashed"


@dataclass(slots=True)
class CrashRound:
    state: RoundState
    multiplier: Decimal
    crash_point: Decimal


class CrashEngine:
    """Isolated crash game engine; provably-fair adapters can be added later."""

    def seed_round(self) -> CrashRound:
        crash_point = Decimal(str(round(random.uniform(1.01, 12.0), 2)))
        return CrashRound(state=RoundState.WAITING, multiplier=Decimal("1.00"), crash_point=crash_point)

    def step(self, round_state: CrashRound) -> CrashRound:
        if round_state.state == RoundState.CRASHED:
            return round_state
        new_multiplier = round(round_state.multiplier + Decimal("0.05"), 2)
        state = RoundState.ACTIVE if new_multiplier < round_state.crash_point else RoundState.CRASHED
        return CrashRound(state=state, multiplier=new_multiplier, crash_point=round_state.crash_point)
