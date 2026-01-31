from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol


class ProcessState(Enum):
    RUNNABLE = auto()
    BLOCKED = auto()
    EXITED = auto()


class DemandModel(Protocol):
    def demand_ms(self, tick: int) -> int: ...


@dataclass(slots=True)
class Process:
    pid: int
    name: str
    demand: DemandModel
    state: ProcessState = ProcessState.RUNNABLE

    def requested_ms(self, tick: int) -> int:
        if self.state is not ProcessState.RUNNABLE:
            return 0
        d = self.demand.demand_ms(tick)
        return d if d > 0 else 0
