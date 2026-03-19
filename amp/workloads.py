from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConstantDemand:
    ms: int

    def demand_ms(self, tick: int) -> int:
        return self.ms


@dataclass(slots=True)
class BurstDemand:
    burst_ms: int
    period: int
    duty: int

    def demand_ms(self, tick: int) -> int:
        phase = tick % self.period
        return self.burst_ms if phase < self.duty else 0

@dataclass(slots=True)
class CryptojackingDemand:
    """Semantic wrapper for a sustained maximum-demand workload.

    Structurally identical to ConstantDemand(ms=demand_ms), but named
    explicitly to document the attack class in experiment code.

    Workload definition:
        ms (demand_ms_per_tick) : should equal DEFAULT_SLICE_MS so the attacker
                             always submits the maximal eligible bid:
                               bid_ms = min(demand_ms, budget, slice_ms)
                             when budget >= slice_ms, bid collapses to
                             slice_ms (maximum possible).
        spawn              : false — single process, no identity amplification.
        idle_ticks         : none, demand_ms is nonzero every tick by
                             construction; attacker never yields voluntarily.
        termination        : bankruptcy (budget <= 0); duration is empirically
                             determined by dispatch frequency, not fixed.

    Scheduling assumption:
        Saturation guarantees eligibility every tick, not guaranteed dispatch.
        Attacker competitiveness depends on bid relative to other processes.

    Invariant:
        Attacker cannot increase its execution share without increasing spend.
        Sustained demand accelerates bankruptcy rather than amplifying
        influence, provided net burn rate (grant_ms - mint_rate_active) > 0.
        Unlike fork bombs, there is no identity amplification lever -- more
        demand does not create more scheduler slots.

    Experiment parameters (scheduler-assigned, not workload-controlled):
        initial_budget : DEFAULT_BUDGET_MS - same as all processes, no-classification principle

    Theoretical upper bound (attacker wins every tick):
        net burn rate = grant_ms - mint_rate_active = 10 - 2 = 8 ms/tick
        → ~7–8 ticks to bankruptcy under continuous dispatch.
    Actual time-to-bankruptcy: determined empirically based on dispatch
        frequency under competition from critical and benign processes.
    """

    ms: int

    def demand_ms(self, tick: int) -> int:
        return self.ms


@dataclass(slots=True)
class ForkBombSpawner:
    spawn_every: int
    spawn_count: int
    max_procs: int
    child_demand_ms: int
    spawn_fee_ms: int
    child_start_budget_ms: int

    def new_children(self, tick: int, current_total: int) -> int:
        if current_total >= self.max_procs:
            return 0
        if self.spawn_every <= 0:
            return 0
        if tick % self.spawn_every != 0:
            return 0
        remaining = self.max_procs - current_total
        return self.spawn_count if self.spawn_count <= remaining else remaining