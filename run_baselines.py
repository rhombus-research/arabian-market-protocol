"""Baseline comparison: RR vs CFS vs Cgroup vs AMP across both attack classes.

Addresses the practicum grader's primary criticism: the baseline cannot be
Round Robin alone. CFS and Cgroup are added as stronger competitors.

Output:
    out/baseline_comparison.json — machine-readable per-config results
    stdout                       — formatted comparison table
"""

from __future__ import annotations

import json
import os
from typing import Sequence

from amp.config import (
    CHILD_START_BUDGET_MS, DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS,
    MINT_RATE_THROTTLED_MS, SPAWN_FEE_MS, TICK_MS,
)
from amp.baselines import CFSScheduler, CgroupScheduler, CgroupConfig
from amp.process import Process
from amp.scheduler import MarketScheduler, RoundRobinScheduler
from amp.sijil import ExecutionState, SijilRecord
from amp.workloads import (
    BurstDemand, ConstantDemand, CryptojackingDemand, ForkBombSpawner,
)

TICKS = 2000
CRITICAL_PID = 1
BENIGN_PID = 2
ATTACKER_PID = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _base_forkbomb_procs() -> list[Process]:
    return [
        Process(pid=CRITICAL_PID, name="critical-burst",
                demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=BENIGN_PID, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=ATTACKER_PID, name="attacker-root", demand=ConstantDemand(ms=10)),
    ]


def _base_cryptojack_procs() -> list[Process]:
    return [
        Process(pid=CRITICAL_PID, name="critical-burst",
                demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=BENIGN_PID, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=ATTACKER_PID, name="attacker-cryptojack",
                demand=CryptojackingDemand(ms=10)),
    ]


def _summarize(dispatch_log: list[dict], max_procs: int, ticks: int) -> dict:
    total = sum(1 for e in dispatch_log if e["dispatch_pid"] is not None)
    idle = ticks - total
    by_pid: dict[int, int] = {}
    crit_ticks: list[int] = []
    for e in dispatch_log:
        pid = e["dispatch_pid"]
        if pid is None:
            continue
        by_pid[pid] = by_pid.get(pid, 0) + 1
        if pid == CRITICAL_PID:
            crit_ticks.append(e["tick"])
    gaps = [b - a for a, b in zip(crit_ticks, crit_ticks[1:])]
    max_gap = max(gaps) if gaps else 0
    return {
        "ticks": ticks,
        "total_dispatches": total,
        "idle_ticks": idle,
        "cpu_utilization": round(total / ticks, 4),
        "critical_dispatches": by_pid.get(CRITICAL_PID, 0),
        "critical_dispatch_ratio": round(by_pid.get(CRITICAL_PID, 0) / total, 4) if total > 0 else 0,
        "critical_max_gap": max_gap,
        "benign_dispatches": by_pid.get(BENIGN_PID, 0),
        "attacker_dispatches": sum(c for pid, c in by_pid.items() if pid >= ATTACKER_PID),
        "max_procs": max_procs,
    }


# ---------------------------------------------------------------------------
# Fork bomb runners
# ---------------------------------------------------------------------------
def _run_forkbomb(scheduler_name: str, scheduler, spawner: ForkBombSpawner,
                  cgroup_assign_fn=None, amp_records: dict | None = None) -> dict:
    procs = _base_forkbomb_procs()
    log: list[dict] = []
    peak = len(procs)

    for tick in range(TICKS):
        # Spawning
        if amp_records is not None:
            # AMP path: spawn fee enforcement
            from amp.scheduler import MarketScheduler  # local import to satisfy type
            assert isinstance(scheduler, MarketScheduler)
            scheduler.forkbomb_spawn(processes=procs, tick=tick,
                                     spawner=spawner, parent_pid=ATTACKER_PID)
        else:
            # Non-AMP path: free spawning, optional cgroup assignment
            to_spawn = spawner.new_children(tick=tick, current_total=len(procs))
            for _ in range(to_spawn):
                new_pid = max(p.pid for p in procs) + 1
                procs.append(Process(pid=new_pid, name=f"attacker-{new_pid}",
                                     demand=ConstantDemand(ms=10)))
                if cgroup_assign_fn is not None:
                    cgroup_assign_fn(new_pid)

        peak = max(peak, len(procs))

        if amp_records is not None:
            scheduler.reconcile_states(procs)
            scheduler.mint(procs)
        d = scheduler.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        log.append({"tick": tick, "dispatch_pid": d.pid, "granted_ms": d.granted_ms})

    summary = _summarize(log, max_procs=peak, ticks=TICKS)
    summary["scheduler"] = scheduler_name
    summary["workload"] = "forkbomb"
    return summary


def run_forkbomb_rr() -> dict:
    spawner = ForkBombSpawner(spawn_every=1, spawn_count=3, max_procs=60,
                              child_demand_ms=10, spawn_fee_ms=0,
                              child_start_budget_ms=0)
    return _run_forkbomb("RR", RoundRobinScheduler(), spawner)


def run_forkbomb_cfs() -> dict:
    spawner = ForkBombSpawner(spawn_every=1, spawn_count=3, max_procs=60,
                              child_demand_ms=10, spawn_fee_ms=0,
                              child_start_budget_ms=0)
    return _run_forkbomb("CFS", CFSScheduler(), spawner)


def run_forkbomb_cgroup(misconfigured: bool = False) -> dict:
    # Period = 10 ticks = 100ms with TICK_MS=10.
    # Well-configured: critical/benign/attacker each in own cgroup.
    # Misconfigured: attacker shares cgroup with critical.
    if misconfigured:
        cgroups = [
            CgroupConfig(name="shared", quota_ms=20, period_ticks=10,
                         pids=[CRITICAL_PID, ATTACKER_PID]),
            CgroupConfig(name="benign", quota_ms=20, period_ticks=10,
                         pids=[BENIGN_PID]),
        ]
        attacker_cgroup = "shared"
        label = "Cgroup-MISCONFIG"
    else:
        cgroups = [
            CgroupConfig(name="critical", quota_ms=20, period_ticks=10,
                         pids=[CRITICAL_PID]),
            CgroupConfig(name="benign", quota_ms=20, period_ticks=10,
                         pids=[BENIGN_PID]),
            CgroupConfig(name="attacker", quota_ms=60, period_ticks=10,
                         pids=[ATTACKER_PID]),
        ]
        attacker_cgroup = "attacker"
        label = "Cgroup"

    sched = CgroupScheduler(cgroups=cgroups, pid_to_cgroup={})

    def assign(pid: int) -> None:
        sched.register_pid(pid, attacker_cgroup)

    spawner = ForkBombSpawner(spawn_every=1, spawn_count=3, max_procs=60,
                              child_demand_ms=10, spawn_fee_ms=0,
                              child_start_budget_ms=0)
    return _run_forkbomb(label, sched, spawner, cgroup_assign_fn=assign)


def run_forkbomb_amp(spawn_fee_ms: int) -> dict:
    procs = _base_forkbomb_procs()
    records = {
        p.pid: SijilRecord(pid=p.pid, budget=DEFAULT_BUDGET_MS, spent=0,
                            state=ExecutionState.ACTIVE, last_bid=0)
        for p in procs
    }
    sched = MarketScheduler(records)
    spawner = ForkBombSpawner(spawn_every=1, spawn_count=3, max_procs=60,
                              child_demand_ms=10, spawn_fee_ms=spawn_fee_ms,
                              child_start_budget_ms=CHILD_START_BUDGET_MS)
    result = _run_forkbomb(f"AMP fee={spawn_fee_ms}", sched, spawner,
                           amp_records=records)
    result["attacker_bankrupt"] = records[ATTACKER_PID].state == ExecutionState.BANKRUPT
    return result


# ---------------------------------------------------------------------------
# Cryptojacking runners
# ---------------------------------------------------------------------------
def _run_cryptojack(scheduler_name: str, scheduler, amp_records: dict | None = None) -> dict:
    procs = _base_cryptojack_procs()
    log: list[dict] = []
    for tick in range(TICKS):
        if amp_records is not None:
            scheduler.reconcile_states(procs)
            scheduler.mint(procs)
        d = scheduler.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        log.append({"tick": tick, "dispatch_pid": d.pid, "granted_ms": d.granted_ms})
    summary = _summarize(log, max_procs=len(procs), ticks=TICKS)
    summary["scheduler"] = scheduler_name
    summary["workload"] = "cryptojacking"
    if amp_records is not None:
        summary["attacker_bankrupt"] = amp_records[ATTACKER_PID].state == ExecutionState.BANKRUPT
    return summary


def run_cryptojack_rr() -> dict:
    return _run_cryptojack("RR", RoundRobinScheduler())


def run_cryptojack_cfs() -> dict:
    return _run_cryptojack("CFS", CFSScheduler())


def run_cryptojack_cgroup(misconfigured: bool = False) -> dict:
    if misconfigured:
        cgroups = [
            CgroupConfig(name="shared", quota_ms=20, period_ticks=10,
                         pids=[CRITICAL_PID, ATTACKER_PID]),
            CgroupConfig(name="benign", quota_ms=20, period_ticks=10,
                         pids=[BENIGN_PID]),
        ]
        label = "Cgroup-MISCONFIG"
    else:
        cgroups = [
            CgroupConfig(name="critical", quota_ms=20, period_ticks=10,
                         pids=[CRITICAL_PID]),
            CgroupConfig(name="benign", quota_ms=20, period_ticks=10,
                         pids=[BENIGN_PID]),
            CgroupConfig(name="attacker", quota_ms=60, period_ticks=10,
                         pids=[ATTACKER_PID]),
        ]
        label = "Cgroup"
    sched = CgroupScheduler(cgroups=cgroups, pid_to_cgroup={})
    return _run_cryptojack(label, sched)


def run_cryptojack_amp() -> dict:
    procs = _base_cryptojack_procs()
    records = {
        p.pid: SijilRecord(pid=p.pid, budget=DEFAULT_BUDGET_MS, spent=0,
                            state=ExecutionState.ACTIVE, last_bid=0)
        for p in procs
    }
    sched = MarketScheduler(records)
    return _run_cryptojack("AMP", sched, amp_records=records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    os.makedirs("out", exist_ok=True)

    fork_results = [
        run_forkbomb_rr(),
        run_forkbomb_cfs(),
        run_forkbomb_cgroup(misconfigured=False),
        run_forkbomb_cgroup(misconfigured=True),
        run_forkbomb_amp(spawn_fee_ms=1),
        run_forkbomb_amp(spawn_fee_ms=5),
        run_forkbomb_amp(spawn_fee_ms=10),
    ]

    crypto_results = [
        run_cryptojack_rr(),
        run_cryptojack_cfs(),
        run_cryptojack_cgroup(misconfigured=False),
        run_cryptojack_cgroup(misconfigured=True),
        run_cryptojack_amp(),
    ]

    # --- Print formatted tables ---
    print("=" * 96)
    print("FORK BOMB — Scheduler Comparison")
    print("=" * 96)
    print(f"{'Scheduler':<20s}  {'CritDisp':>8s}  {'CritRatio':>9s}  {'MaxGap':>6s}  "
          f"{'AtkDisp':>7s}  {'MaxProcs':>8s}  {'CPU%':>5s}  {'Bkrpt':>5s}")
    print("-" * 96)
    for r in fork_results:
        bkrpt = str(r.get("attacker_bankrupt", "—"))
        print(f"{r['scheduler']:<20s}  {r['critical_dispatches']:>8d}  "
              f"{r['critical_dispatch_ratio']:>9.3f}  {r['critical_max_gap']:>6d}  "
              f"{r['attacker_dispatches']:>7d}  {r['max_procs']:>8d}  "
              f"{r['cpu_utilization']*100:>5.1f}  {bkrpt:>5s}")

    print()
    print("=" * 96)
    print("CRYPTOJACKING — Scheduler Comparison")
    print("=" * 96)
    print(f"{'Scheduler':<20s}  {'CritDisp':>8s}  {'CritRatio':>9s}  {'MaxGap':>6s}  "
          f"{'AtkDisp':>7s}  {'MaxProcs':>8s}  {'CPU%':>5s}  {'Bkrpt':>5s}")
    print("-" * 96)
    for r in crypto_results:
        bkrpt = str(r.get("attacker_bankrupt", "—"))
        print(f"{r['scheduler']:<20s}  {r['critical_dispatches']:>8d}  "
              f"{r['critical_dispatch_ratio']:>9.3f}  {r['critical_max_gap']:>6d}  "
              f"{r['attacker_dispatches']:>7d}  {r['max_procs']:>8d}  "
              f"{r['cpu_utilization']*100:>5.1f}  {bkrpt:>5s}")

    path = os.path.join("out", "baseline_comparison.json")
    with open(path, "w") as f:
        json.dump({"forkbomb": fork_results, "cryptojacking": crypto_results}, f, indent=2)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
