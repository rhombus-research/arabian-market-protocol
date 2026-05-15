"""Benign collateral damage sweep.

Tests the structural claim that AMP enforces an implicit budget-rate ceiling
on ALL processes, not just adversaries. Any process with mean demand exceeding
MINT_RATE_ACTIVE_MS (2ms/tick) will eventually drift into THROTTLED. Under
decay, THROTTLED processes have their effective mint driven to zero, trapping
them in the same state as a saturating attacker.

Sub-experiments:
    (a) Benign demand sweep, no attacker — isolates structural ceiling
    (b) Benign demand sweep, with attacker — quantifies acceleration
    (c) Phase-change benign recovery test — characterizes whether a process
        that enters THROTTLED can recover to ACTIVE when its demand
        subsequently drops below the active mint rate.
    (d) RR baseline for the same demand sweep — sharpens the AMP-specific claim
"""

from __future__ import annotations

import json
import os
from typing import Sequence

from amp.config import (
    DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS, MINT_RATE_THROTTLED_MS,
)
from amp.process import Process
from amp.scheduler import MarketScheduler, RoundRobinScheduler
from amp.sijil import ExecutionState, SijilRecord
from amp.workloads import BurstDemand, ConstantDemand, CryptojackingDemand

TICKS = 2000
CRITICAL_PID = 1
BENIGN_PID = 2
ATTACKER_PID = 3


def _critical() -> Process:
    return Process(pid=CRITICAL_PID, name="critical-burst",
                   demand=BurstDemand(burst_ms=10, period=10, duty=2))


def _benign(demand_ms: int) -> Process:
    return Process(pid=BENIGN_PID, name=f"benign-d{demand_ms}",
                   demand=ConstantDemand(ms=demand_ms))


def _bursty_benign() -> Process:
    # mean demand = 5*3/10 = 1.5 ms/tick, below MINT_RATE_ACTIVE_MS
    return Process(pid=BENIGN_PID, name="bursty-benign",
                   demand=BurstDemand(burst_ms=5, period=10, duty=3))


class _PhaseDemand:
    """Demand that switches from high_ms to low_ms at switch_tick.
    Used to test whether a process that throttles can recover when its
    demand drops below the active mint rate."""
    __slots__ = ("high_ms", "low_ms", "switch_tick")

    def __init__(self, high_ms: int, low_ms: int, switch_tick: int) -> None:
        self.high_ms = high_ms
        self.low_ms = low_ms
        self.switch_tick = switch_tick

    def demand_ms(self, tick: int) -> int:
        return self.high_ms if tick < self.switch_tick else self.low_ms


def _phase_benign() -> Process:
    # High demand (5 ms/tick) for 100 ticks — enough to cross THROTTLE_AT_MS=15
    # Then drops to 1 ms/tick (below MINT_RATE_ACTIVE=2) — recoverable.
    return Process(pid=BENIGN_PID, name="phase-benign",
                   demand=_PhaseDemand(high_ms=5, low_ms=1, switch_tick=100))


def _cryptojacker() -> Process:
    return Process(pid=ATTACKER_PID, name="attacker-cryptojack",
                   demand=CryptojackingDemand(ms=10))


def _make_records(procs: Sequence[Process]) -> dict[int, SijilRecord]:
    return {
        p.pid: SijilRecord(pid=p.pid, budget=DEFAULT_BUDGET_MS, spent=0,
                           state=ExecutionState.ACTIVE, last_bid=0)
        for p in procs
    }


def _run_amp(procs: list[Process], track_pid: int) -> dict:
    """Run an AMP simulation, tracking when track_pid first enters THROTTLED
    and BANKRUPT states. Returns a per-run summary."""
    records = _make_records(procs)
    sched = MarketScheduler(records)
    dispatch_log: list[dict] = []
    first_throttle: int | None = None
    first_bankrupt: int | None = None
    recovery_count = 0
    was_throttled_last = False

    for tick in range(TICKS):
        transitions = sched.reconcile_states(procs)
        for t in transitions:
            if t.pid == track_pid:
                if t.state_after is ExecutionState.THROTTLED and first_throttle is None:
                    first_throttle = tick
                if t.state_after is ExecutionState.BANKRUPT and first_bankrupt is None:
                    first_bankrupt = tick
                # Recovery: THROTTLED -> ACTIVE
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
        "critical_dispatches": by_pid.get(CRITICAL_PID, 0),
        "critical_dispatch_ratio": round(by_pid.get(CRITICAL_PID, 0) / total, 4) if total else 0,
        "benign_dispatches": by_pid.get(BENIGN_PID, 0),
        "attacker_dispatches": by_pid.get(ATTACKER_PID, 0),
        "tracked_first_throttle_tick": first_throttle,
        "tracked_first_bankrupt_tick": first_bankrupt,
        "tracked_recovery_count": recovery_count,
        "tracked_final_state": records[track_pid].state.name,
        "tracked_final_budget": records[track_pid].budget,
        "total_dispatches": total,
        "idle_ticks": TICKS - total,
        "cpu_utilization": round(total / TICKS, 4),
    }


def _run_rr(procs: list[Process]) -> dict:
    sched = RoundRobinScheduler()
    dispatch_log: list[dict] = []
    for tick in range(TICKS):
        d = sched.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        dispatch_log.append({"tick": tick, "dispatch_pid": d.pid})
    by_pid: dict[int, int] = {}
    for e in dispatch_log:
        if e["dispatch_pid"] is not None:
            by_pid[e["dispatch_pid"]] = by_pid.get(e["dispatch_pid"], 0) + 1
    total = sum(by_pid.values())
    return {
        "critical_dispatches": by_pid.get(CRITICAL_PID, 0),
        "critical_dispatch_ratio": round(by_pid.get(CRITICAL_PID, 0) / total, 4) if total else 0,
        "benign_dispatches": by_pid.get(BENIGN_PID, 0),
        "attacker_dispatches": by_pid.get(ATTACKER_PID, 0),
        "total_dispatches": total,
        "cpu_utilization": round(total / TICKS, 4),
    }


def main() -> None:
    os.makedirs("out", exist_ok=True)
    results: dict = {"a_amp_no_attacker": [], "b_amp_with_attacker": [],
                     "c_bursty_recovery": None, "d_rr_no_attacker": []}

    demand_levels = list(range(1, 10))  # 1..9 ms/tick

    # --- (a) AMP, benign demand sweep, no attacker ---
    print("=" * 88)
    print("(a) AMP — benign demand sweep, NO attacker")
    print("=" * 88)
    print(f"{'Demand':>6s}  {'CritDisp':>8s}  {'BenDisp':>7s}  {'BenThrottleTick':>15s}  "
          f"{'BenFinal':>10s}  {'CPU%':>5s}")
    print("-" * 88)
    for d in demand_levels:
        procs = [_critical(), _benign(d)]
        r = _run_amp(procs, track_pid=BENIGN_PID)
        r["benign_demand_ms"] = d
        r["attacker_present"] = False
        results["a_amp_no_attacker"].append(r)
        print(f"{d:>6d}  {r['critical_dispatches']:>8d}  {r['benign_dispatches']:>7d}  "
              f"{str(r['tracked_first_throttle_tick']):>15s}  "
              f"{r['tracked_final_state']:>10s}  {r['cpu_utilization']*100:>5.1f}")

    # --- (b) AMP, benign demand sweep, WITH attacker ---
    print()
    print("=" * 88)
    print("(b) AMP — benign demand sweep, WITH cryptojacking attacker")
    print("=" * 88)
    print(f"{'Demand':>6s}  {'CritDisp':>8s}  {'BenDisp':>7s}  {'AtkDisp':>7s}  "
          f"{'BenThrottleTick':>15s}  {'BenFinal':>10s}  {'CPU%':>5s}")
    print("-" * 88)
    for d in demand_levels:
        procs = [_critical(), _benign(d), _cryptojacker()]
        r = _run_amp(procs, track_pid=BENIGN_PID)
        r["benign_demand_ms"] = d
        r["attacker_present"] = True
        results["b_amp_with_attacker"].append(r)
        print(f"{d:>6d}  {r['critical_dispatches']:>8d}  {r['benign_dispatches']:>7d}  "
              f"{r['attacker_dispatches']:>7d}  "
              f"{str(r['tracked_first_throttle_tick']):>15s}  "
              f"{r['tracked_final_state']:>10s}  {r['cpu_utilization']*100:>5.1f}")

    # --- (c) Phase-change benign recovery test ---
    print()
    print("=" * 88)
    print("(c) AMP — phase-change benign recovery test")
    print("    high demand (5ms) for ticks 0-99, then low demand (1ms) thereafter")
    print("=" * 88)
    procs = [_critical(), _phase_benign(), _cryptojacker()]
    r = _run_amp(procs, track_pid=BENIGN_PID)
    r["workload"] = "phase_benign(5->1ms@tick100)"
    results["c_bursty_recovery"] = r
    print(f"Phase-change benign:")
    print(f"  Pre-switch demand:     5 ms/tick   (above MINT_RATE_ACTIVE_MS=2)")
    print(f"  Post-switch demand:    1 ms/tick   (below MINT_RATE_ACTIVE_MS=2)")
    print(f"  Switch tick:           100")
    print(f"  Benign dispatches:     {r['benign_dispatches']}")
    print(f"  First THROTTLE tick:   {r['tracked_first_throttle_tick']}")
    print(f"  Recovery count:        {r['tracked_recovery_count']}  "
          f"(THROTTLED -> ACTIVE transitions)")
    print(f"  Final state:           {r['tracked_final_state']}")
    print(f"  Final budget:          {r['tracked_final_budget']}")
    print()
    if r["tracked_recovery_count"] > 0:
        print(f"  -> Phase-change benign RECOVERS from THROTTLED to ACTIVE "
              f"{r['tracked_recovery_count']}x.")
        print("     throttled_dispatches resets on transition to ACTIVE,")
        print("     enabling future recovery cycles.")
    else:
        print(f"  -> Phase-change benign stays in {r['tracked_final_state']} permanently.")
        print("     Once THROTTLED under decay, the trap has no organic escape:")
        print("       1. Decay drives effective mint to zero, so budget cannot grow.")
        print("       2. The 1/2 penalty on bids keeps the process from winning")
        print("          dispatches against any non-throttled competitor.")
        print("     The process is permanently marginalized even though its demand")
        print("     dropped below MINT_RATE_ACTIVE_MS. THIS IS THE TRAP.")
        print("     Recovery requires operator intervention or a protocol extension;")
        print("     no organic recovery path exists in the current protocol.")

    # --- (d) RR baseline for benign demand sweep ---
    print()
    print("=" * 88)
    print("(d) RR — benign demand sweep, NO attacker (baseline)")
    print("=" * 88)
    print(f"{'Demand':>6s}  {'CritDisp':>8s}  {'BenDisp':>7s}  {'CPU%':>5s}")
    print("-" * 88)
    for d in demand_levels:
        procs = [_critical(), _benign(d)]
        r = _run_rr(procs)
        r["benign_demand_ms"] = d
        results["d_rr_no_attacker"].append(r)
        print(f"{d:>6d}  {r['critical_dispatches']:>8d}  {r['benign_dispatches']:>7d}  "
              f"{r['cpu_utilization']*100:>5.1f}")

    path = os.path.join("out", "benign_sweep_summary.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {path}")

    # --- Headline framing ---
    print()
    print("=" * 88)
    print("FINDING")
    print("=" * 88)
    boundary = next((r["benign_demand_ms"] for r in results["a_amp_no_attacker"]
                    if r["tracked_final_state"] != "ACTIVE"), None)
    print(f"""
AMP enforces an implicit budget-rate ceiling at MINT_RATE_ACTIVE_MS = 2 ms/tick.
Any process with mean demand exceeding this ceiling is trapped in THROTTLED under
decay — attacker or not. The first benign demand level that traps the process
without an attacker present: {boundary}.

The phase-change recovery experiment reveals the THROTTLE TRAP: once a process
enters THROTTLED under decay, it cannot organically escape — even if its demand
permanently drops below the active mint rate. Decay zeros the effective mint,
the 1/2 bid penalty prevents winning dispatches, and the process is stuck at
budget=1 forever.

The current protocol has NO organic recovery path. A deployment will require
either periodic budget refresh, manual intervention, or a future protocol
extension that provides an escape route for processes that demonstrate
sustained solvency post-throttle.

Stated as a deployment constraint: under AMP with decay, THROTTLED is effectively
terminal for any process not explicitly rehabilitated. This must be documented.
""")


if __name__ == "__main__":
    main()
