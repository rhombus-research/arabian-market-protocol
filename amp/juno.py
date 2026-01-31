from dataclasses import dataclass
from enum import Enum, auto


class ExecutionState(Enum):
    ACTIVE = auto()
    THROTTLED = auto()
    BANKRUPT = auto()


@dataclass(slots=True)
class JunoRecord:
    pid: int
    budget: int
    spent: int
    state: ExecutionState
    last_bid: int
