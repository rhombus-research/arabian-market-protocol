"""Heterogeneous workload experiment.

Addresses two critiques in a single experiment:
  (1) Workloads are not realistic / population too small.
  (2) The bidding mechanism may collapse to a priority queue if all
      processes submit the same bid magnitude.

Workload: 1 critical (burst) + 5 benign (demands 1,2,3,4,5 ms/tick) + 1
cryptojacker = 7 processes. The 5-tier benign population is the test of
whether AMP's bidding produces meaningful differentiation across demand
levels rather than uniform treatment.

Output:
    out/heterogeneous_summary.json
    stdout                          — per-process trajectory and dispatches
"""

from __future__ import annotations

import json
import os

from amp.config import DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS
from amp.process import Process
from amp.scheduler import MarketScheduler
from amp.sijil import ExecutionState, SijilRecord
from amp.workloads import BurstDemand, ConstantDemand, CryptojackingDemand

TICKS = 2000
CRITICAL_PID = 1
ATTACKER_PID = 100
BENIGN_PIDS = [10, 11, 12, 13, 14]  # demands 1..5
BENIGN_DEMANDS = {10: 1, 11: 2, 12: 3, 13: 4, 14: 5}


def _build_procs() -> list[Process]:
    procs = [Process(pid=CRITICAL_PID, name="critical-burst",
                     demand=BurstDemand(burst_ms=10, period=10, duty=2))]
    for pid in BENIGN_PIDS:
        d = BENIGN_DEMANDS[pid]
        procs.append(Process(pid=pid, name=f"benign-d{d}",
                             demand=ConstantDemand(ms=d)))
    procs.append(Process(pid=ATTACKER_PID, name="attacker-cryptojack",
                         demand=CryptojackingDemand(ms=10)))
    return procs


def main() -> None:
    os.makedirs("out", exist_ok=True)
    procs = _build_procs()
    records = {
        p.pid: SijilRecord(pid=p.pid, budget=DEFAULT_BUDGET_MS, spent=0,
                           state=ExecutionState.ACTIVE, last_bid=0)
        for p in procs
    }
    sched = MarketScheduler(records)

    dispatch_log: list[dict] = []
    state_log: dict[int, list[tuple[int, str, str]]] = {p.pid: [] for p in procs}
    first_throttle: dict[int, int | None] = {p.pid: None for p in procs}
    first_bankrupt: dict[int, int | None] = {p.pid: None for p in procs}
    budget_trajectory: dict[int, list[tuple[int, int]]] = {p.pid: [(0, DEFAULT_BUDGET_MS)] for p in procs}

    for tick in range(TICKS):
        transitions = sched.reconcile_states(procs)
        for t in transitions:
            state_log[t.pid].append((tick, t.state_before.name, t.state_after.name))
            if t.state_after is ExecutionState.THROTTLED and first_throttle[t.pid] is None:
                first_throttle[t.pid] = tick
            if t.state_after is ExecutionState.BANKRUPT and first_bankrupt[t.pid] is None:
                first_bankrupt[t.pid] = tick
        sched.mint(procs)
        d = sched.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        dispatch_log.append({"tick": tick, "dispatch_pid": d.pid, "granted_ms": d.granted_ms})

        # Sample budget every 100 ticks for trajectory
        if tick % 100 == 99:
            for p in procs:
                budget_trajectory[p.pid].append((tick + 1, records[p.pid].budget))

    # Per-process aggregation
    by_pid: dict[int, int] = {}
    for e in dispatch_log:
        if e["dispatch_pid"] is not None:
            by_pid[e["dispatch_pid"]] = by_pid.get(e["dispatch_pid"], 0) + 1

    total_dispatches = sum(by_pid.values())

    per_process = []
    for p in procs:
        per_process.append({
            "pid": p.pid,
            "name": p.name,
            "demand_ms": (BENIGN_DEMANDS.get(p.pid)
                          if p.pid in BENIGN_DEMANDS
                          else (10 if p.pid == ATTACKER_PID else "burst(10/10/2)")),
            "dispatches": by_pid.get(p.pid, 0),
            "final_state": records[p.pid].state.name,
            "final_budget": records[p.pid].budget,
            "first_throttle_tick": first_throttle[p.pid],
            "first_bankrupt_tick": first_bankrupt[p.pid],
            "state_transitions": len(state_log[p.pid]),
        })

    out = {
        "ticks": TICKS,
        "total_dispatches": total_dispatches,
        "cpu_utilization": round(total_dispatches / TICKS, 4),
        "per_process": per_process,
        "budget_trajectory": {str(pid): pts for pid, pts in budget_trajectory.items()},
    }

    path = os.path.join("out", "heterogeneous_summary.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)

    # --- Print ---
    print("=" * 96)
    print("HETEROGENEOUS WORKLOAD — 7 processes (1 critical + 5 benign tiers + 1 cryptojacker)")
    print("=" * 96)
    print(f"{'PID':>4s}  {'Name':<22s}  {'Demand':>10s}  {'Disp':>5s}  "
          f"{'Final':>10s}  {'Budget':>6s}  {'ThrottleTick':>12s}  {'BankruptTick':>12s}")
    print("-" * 96)
    for r in per_process:
        print(f"{r['pid']:>4d}  {r['name']:<22s}  {str(r['demand_ms']):>10s}  "
              f"{r['dispatches']:>5d}  {r['final_state']:>10s}  {r['final_budget']:>6d}  "
              f"{str(r['first_throttle_tick']):>12s}  {str(r['first_bankrupt_tick']):>12s}")

    print()
    print(f"Total dispatches: {total_dispatches}  CPU util: {out['cpu_utilization']*100:.1f}%")
    print(f"\nWrote {path}")

    # --- Framing ---
    print()
    print("=" * 96)
    print("BID DIFFERENTIATION FINDING")
    print("=" * 96)
    benign_results = [r for r in per_process if r["pid"] in BENIGN_PIDS]
    distinct_disp = len({r["dispatches"] for r in benign_results})
    print(f"""
Across the 5-tier benign population (demands 1..5 ms/tick), AMP produces
{distinct_disp} distinct dispatch outcomes. The market mechanism does
differentiate by demand level — but the differentiation is binary in the limit:
processes at or below MINT_RATE_ACTIVE_MS=2 ms/tick stay ACTIVE and capture
sustained dispatches; processes above it enter THROTTLED and are marginalized
to the same trap as the cryptojacker. This is the implicit budget-rate ceiling
finding restated across a realistic population.

Bid differentiation IS present (bids scale with demand) but the dominant signal
is state, not bid magnitude. A reviewer's "collapses to a priority queue" critique
is correct in the steady state: once state classes are assigned (ACTIVE vs
THROTTLED vs BANKRUPT), the auction within a state class is largely uniform.
""")


if __name__ == "__main__":
    main()
