from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from typing import List

from amp.config import (
    THROTTLE_AT_MS,
    THROTTLE_PENALTY_DEN,
    THROTTLE_PENALTY_NUM,
)
from amp.sijil import ExecutionState, SijilRecord
from amp.process import Process, ProcessState
from amp.workloads import ForkBombSpawner, ConstantDemand


@dataclass(slots=True)
class Dispatch:
    pid: int | None
    granted_ms: int


@dataclass(slots=True)
class StateTransition:
    pid: int
    state_before: ExecutionState
    state_after: ExecutionState


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

    def reconcile_states(self, processes: Sequence[Process]) -> list[StateTransition]:
        """
        Evaluate and apply state transitions for all records before selection.
        Returns a list of transitions that occurred this tick for logging.
        State is a precondition for selection, not a side effect of it.
        """
        transitions: list[StateTransition] = []

        for p in processes:
            r = self._records.get(p.pid)
            if r is None:
                continue

            # BANKRUPT is a terminal state — only minting can reverse it
            if r.state is ExecutionState.BANKRUPT:
                continue

            before = r.state

            if r.budget <= 0:
                after = ExecutionState.BANKRUPT
            elif r.budget <= THROTTLE_AT_MS:
                after = ExecutionState.THROTTLED
            else:
                after = ExecutionState.ACTIVE

            if after != before:
                r.state = after
                transitions.append(StateTransition(pid=p.pid, state_before=before, state_after=after))
        return transitions

    def select(self, processes: Sequence[Process], tick: int, slice_ms: int) -> Dispatch:
        """
        Select one process for execution this tick.
        Reads state as a precondition — does not modify state.
        Budget debit and bankruptcy transition on grant only.
        """
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

        return Dispatch(pid=best_pid, granted_ms=grant)

    def forkbomb_spawn(self, processes: List[Process], tick: int, spawner: ForkBombSpawner, parent_pid: int) -> tuple[int, StateTransition | None]:
        root = self._records.get(parent_pid)
        if root is None:
            return 0, None
        if root.state is ExecutionState.BANKRUPT or root.budget <= 0:
            return 0, None

        desired = spawner.new_children(tick=tick, current_total=len(processes))
        if desired <= 0:
            return 0, None

        affordable = desired
        if spawner.spawn_fee_ms > 0:
            max_affordable = root.budget // spawner.spawn_fee_ms
            if affordable > max_affordable:
                affordable = max_affordable

        spawned = 0
        bankruptcy_transition: StateTransition | None = None
        for _ in range(affordable):
            state_before = root.state
            root.budget -= spawner.spawn_fee_ms
            root.spent += spawner.spawn_fee_ms

            if root.budget <= 0:
                root.budget = 0
                root.state = ExecutionState.BANKRUPT
                bankruptcy_transition = StateTransition(
                    pid=parent_pid,
                    state_before=state_before,
                    state_after=ExecutionState.BANKRUPT,
                )
                break

            new_pid = max(p.pid for p in processes) + 1
            processes.append(
                Process(
                    pid=new_pid,
                    name=f"attacker-{new_pid}",
                    demand=ConstantDemand(ms=spawner.child_demand_ms),
                )
            )
            self._records[new_pid] = SijilRecord(
                pid=new_pid,
                budget=spawner.child_start_budget_ms,
                spent=0,
                state=ExecutionState.ACTIVE,
                last_bid=0,
            )
            spawned += 1

        assert root.budget >= 0
        return spawned, bankruptcy_transition
