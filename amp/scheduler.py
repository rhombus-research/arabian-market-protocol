from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from amp.config import (
    THROTTLE_AT_MS,
    THROTTLE_PENALTY_DEN,
    THROTTLE_PENALTY_NUM,
)
from amp.sijil import ExecutionState, SijilRecord
from amp.process import Process, ProcessState

@dataclass(slots=True)
class Dispatch:
    pid: int | None
    granted_ms: int


class RoundRobinScheduler:
    def __init__(self) -> None:
        self._cursor = 0

    def select(self, processes: Sequence[Process], tick: int, slice_ms: int) -> Dispatch:
        runnable = [p for p in processes if p.state is ProcessState.RUNNABLE and p.requested_ms(tick) > 0]
        if not runnable:
            return Dispatch(pid=None, granted_ms=0)

        self._cursor %= len(runnable)
        p = runnable[self._cursor]
        self._cursor = (self._cursor + 1) % len(runnable)

        req = p.requested_ms(tick)
        grant = slice_ms if req >= slice_ms else req
        return Dispatch(pid=p.pid, granted_ms=grant)


class MarketScheduler:
    def __init__(self, records: dict[int, SijilRecord]) -> None:
        self._records = records

    def select(self, processes: Sequence[Process], tick: int, slice_ms: int) -> Dispatch:
        best_pid: int | None = None
        best_bid = 0

        for p in processes:
            if p.state is not ProcessState.RUNNABLE:
                continue

            r = self._records.get(p.pid)
            if r is None or r.state is ExecutionState.BANKRUPT:
                continue

            req = p.requested_ms(tick)
            if req <= 0 or r.budget <= 0:
                continue

            r.state = ExecutionState.THROTTLED if r.budget <= THROTTLE_AT_MS else ExecutionState.ACTIVE

            bid = req if req < r.budget else r.budget
            if bid > slice_ms:
                bid = slice_ms

            if r.state is ExecutionState.THROTTLED:
                bid = (bid * THROTTLE_PENALTY_NUM) // THROTTLE_PENALTY_DEN

            r.last_bid = bid

            if bid > best_bid:
                best_bid = bid
                best_pid = p.pid

        if best_pid is None or best_bid <= 0:
            return Dispatch(pid=None, granted_ms=0)

        r = self._records[best_pid]
        grant = best_bid if best_bid <= r.budget else r.budget

        r.budget -= grant
        r.spent += grant

        if r.budget <= 0:
            r.budget = 0
            r.state = ExecutionState.BANKRUPT

        return Dispatch(pid=best_pid, granted_ms=grant)
