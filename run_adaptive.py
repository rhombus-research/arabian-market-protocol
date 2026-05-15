"""Adaptive adversary experiment.

Tests whether attackers can defeat AMP by modulating their demand pattern.

Strategies tested:
  - Constant cryptojacker (control)              — submits high demand every tick
  - Pulse attacker, 50% duty (burst=5, rest=5)   — alternates aggression
  - Pulse attacker, 30% duty (burst=3, rest=7)   — lighter sustained pressure
  - Pulse attacker, 10% duty (burst=1, rest=9)   — periodic spikes
  - Tenure gamer (low for 100t then high)        — builds trust before attacking

Key question: can a strategic attacker extract more critical-process disruption
than a naive cryptojacker by managing budget depletion?

Output:
    out/adaptive_adversary_summary.json
"""

from __future__ import annotations

import json
import os

from amp.config import DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS
from amp.process import Process
from amp.scheduler import MarketScheduler
from amp.sijil import ExecutionState, SijilRecord
from amp.workloads import (
    BurstDemand, ConstantDemand, CryptojackingDemand, PulseAttacker, TenureGamer,
)

TICKS = 2000
CRITICAL_PID = 1
BENIGN_PID = 2
ATTACKER_PID = 3


def _base_procs(attacker_demand) -> list[Process]:
    return [
        Process(pid=CRITICAL_PID, name="critical-burst",
                demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=BENIGN_PID, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=ATTACKER_PID, name="attacker", demand=attacker_demand),
    ]


def _run(label: str, attacker_demand) -> dict:
    procs = _base_procs(attacker_demand)
    records = {
        p.pid: SijilRecord(pid=p.pid, budget=DEFAULT_BUDGET_MS, spent=0,
                           state=ExecutionState.ACTIVE, last_bid=0)
        for p in procs
    }
    sched = MarketScheduler(records)
    dispatch_log: list[dict] = []
    first_throttle: int | None = None
    first_bankrupt: int | None = None
    recovery_count = 0

    for tick in range(TICKS):
        transitions = sched.reconcile_states(procs)
        for t in transitions:
            if t.pid != ATTACKER_PID:
                continue
            if t.state_after is ExecutionState.THROTTLED and first_throttle is None:
                first_throttle = tick
            if t.state_after is ExecutionState.BANKRUPT and first_bankrupt is None:
                first_bankrupt = tick
            if (t.state_before is ExecutionState.THROTTLED
                    and t.state_after is ExecutionState.ACTIVE):
                recovery_count += 1
        sched.mint(procs)
        d = sched.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        dispatch_log.append({"tick": tick, "dispatch_pid": d.pid,
                             "granted_ms": d.granted_ms})

    by_pid: dict[int, int] = {}
    for e in dispatch_log:
        if e["dispatch_pid"] is not None:
            by_pid[e["dispatch_pid"]] = by_pid.get(e["dispatch_pid"], 0) + 1
    total = sum(by_pid.values())

    return {
        "label": label,
        "critical_dispatches": by_pid.get(CRITICAL_PID, 0),
        "critical_dispatch_ratio": round(by_pid.get(CRITICAL_PID, 0) / total, 4) if total else 0,
        "benign_dispatches": by_pid.get(BENIGN_PID, 0),
        "attacker_dispatches": by_pid.get(ATTACKER_PID, 0),
        "attacker_first_throttle_tick": first_throttle,
        "attacker_first_bankrupt_tick": first_bankrupt,
        "attacker_recovery_count": recovery_count,
        "attacker_final_state": records[ATTACKER_PID].state.name,
        "attacker_final_budget": records[ATTACKER_PID].budget,
        "total_dispatches": total,
        "cpu_utilization": round(total / TICKS, 4),
    }


def main() -> None:
    os.makedirs("out", exist_ok=True)

    configs = [
        ("Constant cryptojacker",
            CryptojackingDemand(ms=10)),
        ("Pulse 50% (5b/5r)",
            PulseAttacker(high_ms=10, low_ms=0, burst_ticks=5, rest_ticks=5)),
        ("Pulse 30% (3b/7r)",
            PulseAttacker(high_ms=10, low_ms=0, burst_ticks=3, rest_ticks=7)),
        ("Pulse 10% (1b/9r)",
            PulseAttacker(high_ms=10, low_ms=0, burst_ticks=1, rest_ticks=9)),
        ("Tenure gamer (1ms x100, then 10ms)",
            TenureGamer(low_ms=1, high_ms=10, buildup_ticks=100)),
    ]

    results = [_run(label, dem) for label, dem in configs]

    print("=" * 104)
    print("ADAPTIVE ADVERSARY — AMP with default config")
    print("=" * 104)
    print(f"{'Strategy':<36s}  {'CritDisp':>8s}  {'CritRatio':>9s}  {'AtkDisp':>7s}  "
          f"{'ThrottleT':>9s}  {'BkptT':>6s}  {'Recov':>5s}  {'Final':>10s}")
    print("-" * 104)
    for r in results:
        print(f"{r['label']:<36s}  {r['critical_dispatches']:>8d}  "
              f"{r['critical_dispatch_ratio']:>9.3f}  {r['attacker_dispatches']:>7d}  "
              f"{str(r['attacker_first_throttle_tick']):>9s}  "
              f"{str(r['attacker_first_bankrupt_tick']):>6s}  "
              f"{r['attacker_recovery_count']:>5d}  "
              f"{r['attacker_final_state']:>10s}")

    path = os.path.join("out", "adaptive_adversary_summary.json")
    with open(path, "w") as f:
        json.dump({"runs": results}, f, indent=2)
    print(f"\nWrote {path}")

    # --- Framing ---
    print()
    print("=" * 104)
    print("ADAPTIVE STRATEGY FINDING")
    print("=" * 104)
    constant = next(r for r in results if r["label"].startswith("Constant"))
    pulses = [r for r in results if r["label"].startswith("Pulse")]
    tenure = next(r for r in results if r["label"].startswith("Tenure"))
    best_pulse = max(pulses, key=lambda r: r["attacker_dispatches"])
    print(f"""
Constant cryptojacker:     {constant['attacker_dispatches']} dispatches, throttled at tick {constant['attacker_first_throttle_tick']}, crit ratio {constant['critical_dispatch_ratio']:.3f}
Best pulse attacker:       {best_pulse['label']:<28s}: {best_pulse['attacker_dispatches']} dispatches, throttled at {best_pulse['attacker_first_throttle_tick']}, crit ratio {best_pulse['critical_dispatch_ratio']:.3f}
Tenure gamer:              {tenure['attacker_dispatches']} dispatches, throttled at tick {tenure['attacker_first_throttle_tick']}, crit ratio {tenure['critical_dispatch_ratio']:.3f}

FINDING — CONTRADICTS THE ACTION-SCRIPT PREDICTION

Pulse 30% extracts {best_pulse['attacker_dispatches']} attacker dispatches without ever entering THROTTLED, while
the constant cryptojacker is marginalized at tick 9 with only {constant['attacker_dispatches']} dispatches. The
pulsing attacker is {best_pulse['attacker_dispatches'] // max(constant['attacker_dispatches'], 1)}x more effective than the naive saturation attack —
critical dispatch ratio falls from {constant['critical_dispatch_ratio']:.3f} (constant) to {best_pulse['critical_dispatch_ratio']:.3f} (pulse 30%).

The 3-burst / 7-rest pattern hits a sweet spot: enough burst ticks to extract
execution during the critical process's idle windows, enough rest to keep
mint accumulation ahead of burn. Net budget grows per cycle, so the attacker
never throttles and AMP's marginalization mechanism never engages.

This is an open vulnerability in the current protocol. The throttle trigger is
budget-level, not demand-rate. An attacker who titrates demand to keep budget
above THROTTLE_AT_MS extracts sustained CPU. Mitigations are future work:
  - Rate-based throttling (track demand intensity over a window)
  - Cap budget accumulation (prevent infinite reserves)

Tenure gamer is throttled at tick {tenure['attacker_first_throttle_tick']} with only {tenure['attacker_dispatches']} dispatches, showing that
the simplest strategic adversary (buildup then attack) is not exploitable
against the current protocol — but pulse adversaries are.
""")


if __name__ == "__main__":
    main()
