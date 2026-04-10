from __future__ import annotations

import asyncio
import copy
from collections import deque
from typing import AsyncGenerator

from amp.config import CHILD_START_BUDGET_MS, DEFAULT_SLICE_MS
from amp.sijil import ExecutionState, SijilRecord
from amp.process import Process, ProcessState
from amp.scheduler import MarketScheduler, RoundRobinScheduler
from amp.workloads import (
    BurstDemand,
    ConstantDemand,
    CryptojackingDemand,
    ForkBombSpawner,
)

from api.models import (
    MarketSchedulerTick,
    MintEvent,
    ProcessSnapshot,
    SchedulerTick,
    SimulationConfig,
    Scenario,
    SystemMetrics,
    TickEvent,
    TransitionEvent,
)


class SimulationEngine:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.tick = 0
        self.running = False
        self.paused = False

        # Build process lists
        self._rr_procs: list[Process] = []
        self._market_procs: list[Process] = []
        self._records: dict[int, SijilRecord] = {}
        self._spawner: ForkBombSpawner | None = None
        self._attacker_root_pid: int | None = None

        # CPU share tracking (rolling window)
        self._rr_grants: dict[int, deque[int]] = {}
        self._market_grants: dict[int, deque[int]] = {}
        self._window_size = 50

        # Critical dispatch tracking
        self._rr_critical_dispatches = 0
        self._market_critical_dispatches = 0
        self._total_ticks = 0

        self._build_processes()

    def _build_processes(self) -> None:
        cfg = self.config
        pid = 1
        base: list[Process] = []

        # Critical tasks
        for i in range(cfg.critical_task_count):
            base.append(
                Process(
                    pid=pid,
                    name=f"critical-{pid}" if cfg.critical_task_count > 1 else "critical-burst",
                    demand=BurstDemand(burst_ms=cfg.default_slice_ms, period=10, duty=2),
                )
            )
            pid += 1

        # Benign process
        base.append(Process(pid=pid, name="benign", demand=ConstantDemand(ms=3)))
        pid += 1

        if cfg.scenario == Scenario.FORKBOMB:
            # Attacker root
            self._attacker_root_pid = pid
            base.append(
                Process(pid=pid, name="attacker-root", demand=ConstantDemand(ms=cfg.default_slice_ms))
            )
            pid += 1

            self._spawner = ForkBombSpawner(
                spawn_every=cfg.spawn_every,
                spawn_count=3,
                max_procs=cfg.fork_bomb_count,
                child_demand_ms=cfg.default_slice_ms,
                spawn_fee_ms=cfg.spawn_fee_ms,
                child_start_budget_ms=cfg.child_start_budget_ms,
            )

        elif cfg.scenario == Scenario.CRYPTOJACKING:
            for i in range(cfg.crypto_miner_count):
                base.append(
                    Process(
                        pid=pid,
                        name=f"cryptojack-{pid}" if cfg.crypto_miner_count > 1 else "attacker-cryptojack",
                        demand=CryptojackingDemand(ms=cfg.default_slice_ms),
                    )
                )
                pid += 1

        # Deep copy for independent RR and Market runs
        self._rr_procs = copy.deepcopy(base)
        self._market_procs = copy.deepcopy(base)

        # Initialize SijilRecords for market processes
        self._records = {
            p.pid: SijilRecord(
                pid=p.pid,
                budget=cfg.default_budget_ms,
                spent=0,
                state=ExecutionState.ACTIVE,
                last_bid=0,
            )
            for p in self._market_procs
        }

        # Initialize schedulers
        self._rr = RoundRobinScheduler()
        self._market = MarketScheduler(self._records)

        # RR fork bomb spawner (no fees, just spawns)
        if cfg.scenario == Scenario.FORKBOMB:
            self._rr_spawner = ForkBombSpawner(
                spawn_every=cfg.spawn_every,
                spawn_count=3,
                max_procs=cfg.fork_bomb_count,
                child_demand_ms=cfg.default_slice_ms,
                spawn_fee_ms=0,  # RR has no spawn fee concept
                child_start_budget_ms=cfg.child_start_budget_ms,
            )

    def _snapshot_rr_processes(self) -> list[ProcessSnapshot]:
        snapshots = []
        for p in self._rr_procs:
            total_grants = sum(
                sum(g) for g in self._rr_grants.values()
            )
            pid_grants = sum(self._rr_grants.get(p.pid, deque()))
            cpu_share = (pid_grants / total_grants * 100) if total_grants > 0 else 0.0

            snapshots.append(
                ProcessSnapshot(
                    pid=p.pid,
                    name=p.name,
                    process_state=p.state.name,
                    cpu_share_pct=round(cpu_share, 1),
                )
            )
        return snapshots

    def _snapshot_market_processes(self) -> list[ProcessSnapshot]:
        snapshots = []
        for p in self._market_procs:
            r = self._records.get(p.pid)
            snapshots.append(
                ProcessSnapshot(
                    pid=p.pid,
                    name=p.name,
                    process_state=p.state.name,
                    execution_state=r.state.name if r else None,
                    budget=r.budget if r else None,
                    spent=r.spent if r else None,
                    last_bid=r.last_bid if r else None,
                )
            )
        return snapshots

    def _track_grant(self, grants: dict[int, deque[int]], pid: int | None, granted_ms: int) -> None:
        if pid is not None:
            if pid not in grants:
                grants[pid] = deque(maxlen=self._window_size)
            grants[pid].append(granted_ms)

    def _step(self, tick: int) -> TickEvent:
        cfg = self.config
        transitions: list[TransitionEvent] = []
        mints: list[MintEvent] = []

        # === RR Side ===

        # RR fork bomb spawning (no fees)
        if cfg.scenario == Scenario.FORKBOMB:
            to_spawn = self._rr_spawner.new_children(tick=tick, current_total=len(self._rr_procs))
            for _ in range(to_spawn):
                new_pid = max(p.pid for p in self._rr_procs) + 1
                self._rr_procs.append(
                    Process(pid=new_pid, name=f"attacker-{new_pid}", demand=ConstantDemand(ms=cfg.default_slice_ms))
                )

        rr_dispatch = self._rr.select(self._rr_procs, tick=tick, slice_ms=cfg.default_slice_ms)
        self._track_grant(self._rr_grants, rr_dispatch.pid, rr_dispatch.granted_ms)

        # === Market Side ===

        # Market fork bomb spawning (with fees)
        if cfg.scenario == Scenario.FORKBOMB and self._spawner and self._attacker_root_pid:
            spawned, spawn_bankruptcy = self._market.forkbomb_spawn(
                processes=self._market_procs,
                tick=tick,
                spawner=self._spawner,
                parent_pid=self._attacker_root_pid,
            )
            if spawn_bankruptcy:
                transitions.append(
                    TransitionEvent(
                        pid=spawn_bankruptcy.pid,
                        from_state=spawn_bankruptcy.state_before.name,
                        to_state=spawn_bankruptcy.state_after.name,
                    )
                )

        # Reconcile states
        state_transitions = self._market.reconcile_states(self._market_procs)
        for t in state_transitions:
            transitions.append(
                TransitionEvent(pid=t.pid, from_state=t.state_before.name, to_state=t.state_after.name)
            )

        # Mint
        mint_events = self._market.mint(self._market_procs, mint_rate_throttled=cfg.mint_rate_throttled_ms)
        for m in mint_events:
            mints.append(MintEvent(pid=m["pid"], minted_ms=m["minted_ms"], state=m["state"]))

        # Select
        market_dispatch = self._market.select(self._market_procs, tick=tick, slice_ms=cfg.default_slice_ms)
        self._track_grant(self._market_grants, market_dispatch.pid, market_dispatch.granted_ms)

        # === Metrics ===
        self._total_ticks += 1
        critical_pids = {p.pid for p in self._market_procs if "critical" in p.name}

        if rr_dispatch.pid and rr_dispatch.pid in critical_pids:
            self._rr_critical_dispatches += 1
        if market_dispatch.pid and market_dispatch.pid in critical_pids:
            self._market_critical_dispatches += 1

        rr_runnable = sum(1 for p in self._rr_procs if p.state is ProcessState.RUNNABLE)
        market_runnable = sum(
            1 for p in self._market_procs
            if p.state is ProcessState.RUNNABLE
            and self._records.get(p.pid) is not None
            and self._records[p.pid].state is not ExecutionState.BANKRUPT
        )

        market_throttled = sum(
            1 for r in self._records.values() if r.state is ExecutionState.THROTTLED
        )
        market_bankrupt = sum(
            1 for r in self._records.values() if r.state is ExecutionState.BANKRUPT
        )

        rr_load = 100.0 if rr_dispatch.pid is not None else 0.0
        market_load = 100.0 if market_dispatch.pid is not None else 0.0

        return TickEvent(
            tick=tick,
            scenario=cfg.scenario.value,
            rr=SchedulerTick(
                dispatch_pid=rr_dispatch.pid,
                granted_ms=rr_dispatch.granted_ms,
                process_count=len(self._rr_procs),
                processes=self._snapshot_rr_processes(),
            ),
            market=MarketSchedulerTick(
                dispatch_pid=market_dispatch.pid,
                granted_ms=market_dispatch.granted_ms,
                process_count=len(self._market_procs),
                processes=self._snapshot_market_processes(),
                transitions=transitions,
                mints=mints,
            ),
            system=SystemMetrics(
                rr_load_pct=rr_load,
                market_load_pct=market_load,
                rr_throttled_count=0,
                market_throttled_count=market_throttled,
                market_bankrupt_count=market_bankrupt,
                critical_dispatch_ratio_rr=(
                    self._rr_critical_dispatches / self._total_ticks
                    if self._total_ticks > 0 else 0.0
                ),
                critical_dispatch_ratio_market=(
                    self._market_critical_dispatches / self._total_ticks
                    if self._total_ticks > 0 else 0.0
                ),
            ),
        )

    async def tick_loop(self) -> AsyncGenerator[TickEvent, None]:
        self.running = True
        self.tick = 0
        delay = self.config.tick_delay_ms / 1000.0
        max_ticks = self.config.ticks if self.config.ticks > 0 else None

        try:
            while self.running:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue

                event = self._step(self.tick)
                yield event

                self.tick += 1
                if max_ticks and self.tick >= max_ticks:
                    break

                await asyncio.sleep(delay)
        finally:
            self.running = False

    def stop(self) -> None:
        self.running = False

    def set_speed(self, tick_delay_ms: int) -> None:
        self.config.tick_delay_ms = max(10, min(2000, tick_delay_ms))

    def tune(self, params: dict) -> None:
        """Live-tune safe economic parameters during a running simulation."""
        if 'mint_rate_throttled_ms' in params:
            val = max(0, min(5, int(params['mint_rate_throttled_ms'])))
            self.config.mint_rate_throttled_ms = val

        if 'spawn_fee_ms' in params:
            val = max(1, min(15, int(params['spawn_fee_ms'])))
            self.config.spawn_fee_ms = val
            # Update the spawner if it exists
            if self._spawner:
                self._spawner.spawn_fee_ms = val
