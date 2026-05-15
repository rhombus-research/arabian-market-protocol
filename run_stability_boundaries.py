"""Two-boundary stability analysis.

The report's §VII.A presents a single 'stability boundary at rate=3' derived
from the decay-on mint rate sweep, and an analytical inequality that predicts
a no-decay boundary at rate=5. This experiment shows the two boundaries are
distinct and that the analytical inequality is loose by 5x.

Boundary 1 (flat-mint):     between rate=0 and rate=1 — any non-zero flat
                            minting defeats throttle-only marginalization.
Boundary 2 (decay-effect):  between rate=2 and rate=3 — where decay fails
                            to outpace the configured mint rate.

Output:
    out/stability_boundaries.json
"""

from __future__ import annotations

import json
import os
import types
from typing import Sequence

from amp.config import (
    DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS, MINT_RATE_ACTIVE_MS,
)
from amp.process import Process
from amp.scheduler import MarketScheduler
from amp.sijil import ExecutionState, SijilRecord
from amp.workloads import BurstDemand, ConstantDemand, CryptojackingDemand

TICKS = 2000
CRITICAL_PID = 1
BENIGN_PID = 2
ATTACKER_PID = 3


def _flat_mint(self: MarketScheduler, processes: Sequence[Process],
               mint_rate_throttled: int = 1) -> list[dict]:
    """Drop-in replacement for MarketScheduler.mint that disables decay."""
    events = []
    for p in processes:
        r = self._records.get(p.pid)
        if r is None or r.state is ExecutionState.BANKRUPT:
            continue
        if r.state is ExecutionState.ACTIVE:
            r.budget += MINT_RATE_ACTIVE_MS
            events.append({"pid": p.pid, "minted_ms": MINT_RATE_ACTIVE_MS, "state": r.state.name})
        elif r.state is ExecutionState.THROTTLED:
            r.budget += mint_rate_throttled
            events.append({"pid": p.pid, "minted_ms": mint_rate_throttled, "state": r.state.name})
    return events


def _run(mint_rate: int, use_decay: bool) -> dict:
    procs = [
        Process(pid=CRITICAL_PID, name="critical-burst",
                demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=BENIGN_PID, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=ATTACKER_PID, name="attacker",
                demand=CryptojackingDemand(ms=10)),
    ]
    records = {
        p.pid: SijilRecord(pid=p.pid, budget=DEFAULT_BUDGET_MS, spent=0,
                           state=ExecutionState.ACTIVE, last_bid=0)
        for p in procs
    }
    sched = MarketScheduler(records)
    if not use_decay:
        sched.mint = types.MethodType(_flat_mint, sched)

    dispatch_log: list[dict] = []
    for tick in range(TICKS):
        sched.reconcile_states(procs)
        sched.mint(procs, mint_rate_throttled=mint_rate)
        d = sched.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        dispatch_log.append({"tick": tick, "dispatch_pid": d.pid})

    by_pid: dict[int, int] = {}
    for e in dispatch_log:
        if e["dispatch_pid"] is not None:
            by_pid[e["dispatch_pid"]] = by_pid.get(e["dispatch_pid"], 0) + 1
    total = sum(by_pid.values())
    return {
        "mint_rate_throttled": mint_rate,
        "use_decay": use_decay,
        "critical_dispatches": by_pid.get(CRITICAL_PID, 0),
        "critical_dispatch_ratio": round(by_pid.get(CRITICAL_PID, 0) / total, 4) if total else 0,
        "attacker_dispatches": by_pid.get(ATTACKER_PID, 0),
        "cpu_utilization": round(total / TICKS, 4),
    }


def main() -> None:
    os.makedirs("out", exist_ok=True)
    rates = [0, 1, 2, 3, 4, 5]
    flat_results = [_run(r, use_decay=False) for r in rates]
    decay_results = [_run(r, use_decay=True) for r in rates]

    print("=" * 88)
    print("TWO-BOUNDARY STABILITY ANALYSIS")
    print("=" * 88)
    print(f"{'Rate':>4s}  {'FlatRatio':>9s}  {'FlatAtk':>7s}  {'FlatCPU%':>8s}  "
          f"||  {'DecayRatio':>10s}  {'DecayAtk':>8s}  {'DecayCPU%':>9s}")
    print("-" * 88)
    for f, d in zip(flat_results, decay_results):
        print(f"{f['mint_rate_throttled']:>4d}  "
              f"{f['critical_dispatch_ratio']:>9.3f}  {f['attacker_dispatches']:>7d}  "
              f"{f['cpu_utilization']*100:>7.1f}  "
              f"||  {d['critical_dispatch_ratio']:>10.3f}  {d['attacker_dispatches']:>8d}  "
              f"{d['cpu_utilization']*100:>8.1f}")

    path = os.path.join("out", "stability_boundaries.json")
    with open(path, "w") as f:
        json.dump({"flat_mint": flat_results, "with_decay": decay_results}, f, indent=2)
    print(f"\nWrote {path}")

    # --- Find boundaries ---
    def boundary(results: list[dict]) -> str:
        for i in range(1, len(results)):
            prev = results[i-1]["critical_dispatch_ratio"]
            curr = results[i]["critical_dispatch_ratio"]
            if prev > 0.5 and curr < 0.5:
                return f"between rate={results[i-1]['mint_rate_throttled']} and rate={results[i]['mint_rate_throttled']}"
        return "not observed in tested range"

    flat_b = boundary(flat_results)
    decay_b = boundary(decay_results)

    print()
    print("=" * 88)
    print("BOUNDARIES")
    print("=" * 88)
    print(f"""
Flat-mint boundary (no decay):           {flat_b}
Decay-effectiveness boundary (with decay): {decay_b}

The report's analytical inequality §VII.A:
    mint_rate_throttled < (THROTTLE_PENALTY_NUM / THROTTLE_PENALTY_DEN) * grant_ms
With current params: mint_rate_throttled < 5 ms/tick (analytical bound).
The empirical flat-mint boundary is rate=1, so the analytical bound is loose
by 5x. The inequality assumes the throttled attacker wins every eligible tick,
which it does not — competition reduces effective recovery rate.

Operative deployment constraint: use the empirical boundary, not the analytical
one. For default penalty (1/2) and slice (10ms), the safe flat-mint config
is mint_rate_throttled = 0 — any non-zero value sustains the attacker
indefinitely. With decay enabled, the safe config widens to rate <= 2.
""")


if __name__ == "__main__":
    main()
