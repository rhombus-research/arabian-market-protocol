from __future__ import annotations

import json
import os
from typing import Any

from amp.config import CHILD_START_BUDGET_MS, DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS, SPAWN_FEE_MS
from amp.sijil import ExecutionState, SijilRecord
from amp.metrics import MetricsRecorder, critical_responsiveness, write_summary
from amp.process import Process
from amp.scheduler import MarketScheduler, RoundRobinScheduler
from amp.workloads import BurstDemand, ConstantDemand, ForkBombSpawner


def _write_jsonl(path: str, events: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _base_processes() -> list[Process]:
    return [
        Process(pid=1, name="critical-burst", demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=2, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=3, name="attacker-root", demand=ConstantDemand(ms=10)),
    ]


def _aggregate_waiting_latency(events_by_pid: dict[int, list[int]], pid: int) -> tuple[float | None, float | None]:
    vals = events_by_pid.get(pid, [])
    if not vals:
        return None, None
    return max(vals), sum(vals) / len(vals)


def run_rr_forkbomb(spawner: ForkBombSpawner, ticks: int, jsonl_path: str, txt_path: str) -> dict[str, Any]:
    rr_procs = _base_processes()
    rr = RoundRobinScheduler()

    # RR latency tracking
    rr_runnable_since: dict[int, int] = {}
    rr_waiting_latency: dict[int, list[int]] = {}

    rr_rec = MetricsRecorder(run_name="forkbomb_rr")

    with open(txt_path, "w", encoding="utf-8") as rr_out:
        rr_out.write("=== Round Robin (Fork Bomb) ===\n")

        for tick in range(ticks):

            to_spawn = spawner.new_children(tick=tick, current_total=len(rr_procs))

            for _ in range(to_spawn):
                new_pid = max(p.pid for p in rr_procs) + 1
                rr_procs.append(Process(pid=new_pid, name=f"attacker-{new_pid}", demand=ConstantDemand(ms=10)))

            for p in rr_procs:
                demand = p.demand.demand_ms(tick)
                if demand > 0:
                    if p.pid not in rr_runnable_since:
                        rr_runnable_since[p.pid] = tick
                else:
                    if p.pid in rr_runnable_since:
                        del rr_runnable_since[p.pid]

            d = rr.select(rr_procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)

            rr_latency = None
            if d.pid is not None and d.pid in rr_runnable_since:
                start_tick = rr_runnable_since[d.pid]
                rr_latency = tick - start_tick
                rr_waiting_latency.setdefault(d.pid, []).append(rr_latency)

            rr_out.write(f"tick={tick:02d} procs={len(rr_procs):02d} dispatch pid={d.pid} grant_ms={d.granted_ms}\n")
            rr_rec.add(
                {
                    "tick": tick,
                    "scheduler": "RR",
                    "procs": len(rr_procs),
                    "dispatch_pid": d.pid,
                    "granted_ms": d.granted_ms,
                    "waiting_latency": rr_latency,
                }
            )

    _write_jsonl(jsonl_path, rr_rec._events)

    rr_sum = rr_rec.summary()
    rr_sum["critical"] = critical_responsiveness(rr_rec._events, critical_pid=1)

    wmax, wmean = _aggregate_waiting_latency(rr_waiting_latency, pid=1)
    rr_sum["critical_wait_max"] = wmax
    rr_sum["critical_wait_mean"] = wmean
    return rr_sum


def run_market_with_fee(spawner: ForkBombSpawner, ticks: int, jsonl_path: str, txt_path: str) -> dict[str, Any]:
    market_procs = _base_processes()

    records: dict[int, SijilRecord] = {
        p.pid: SijilRecord(
            pid=p.pid,
            budget=DEFAULT_BUDGET_MS,
            spent=0,
            state=ExecutionState.ACTIVE,
            last_bid=0,
        )
        for p in market_procs
    }

    market = MarketScheduler(records)

    # Arabian Market latency tracking
    runnable_since: dict[int, int] = {}
    waiting_latency: dict[int, list[int]] = {}

    market_rec = MetricsRecorder(run_name=f"forkbomb_market_fee_{spawner.spawn_fee_ms}")

    attacker_root_pid = 3

    with open(txt_path, "w", encoding="utf-8") as out:
        out.write(f"=== Market (Fork Bomb) fee={spawner.spawn_fee_ms} ===\n")

        for tick in range(ticks):
            market.forkbomb_spawn(
                processes=market_procs,
                tick=tick,
                spawner=spawner,
                parent_pid=attacker_root_pid,
            )

            for p in market_procs:
                demand = p.demand.demand_ms(tick)
                if demand > 0:
                    if p.pid not in runnable_since:
                        runnable_since[p.pid] = tick
                else:
                    if p.pid in runnable_since:
                        del runnable_since[p.pid]

            d = market.select(market_procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)

            latency = None
            if d.pid is not None and d.pid in runnable_since:
                start_tick = runnable_since[d.pid]
                latency = tick - start_tick
                waiting_latency.setdefault(d.pid, []).append(latency)

            out.write(
                f"tick={tick:02d} procs={len(market_procs):02d} dispatch pid={d.pid} grant_ms={d.granted_ms}\n"
            )
            market_rec.add(
                {
                    "tick": tick,
                    "scheduler": "MARKET",
                    "spawn_fee_ms": spawner.spawn_fee_ms,
                    "procs": len(market_procs),
                    "dispatch_pid": d.pid,
                    "granted_ms": d.granted_ms,
                    "waiting_latency": latency,
                }
            )

    _write_jsonl(jsonl_path, market_rec._events)

    market_sum = market_rec.summary()
    market_sum["spawn_fee_ms"] = spawner.spawn_fee_ms
    market_sum["critical"] = critical_responsiveness(market_rec._events, critical_pid=1)

    wmax, wmean = _aggregate_waiting_latency(waiting_latency, pid=1)
    market_sum["critical_wait_max"] = wmax
    market_sum["critical_wait_mean"] = wmean
    return market_sum


def run_forkbomb_rr_and_market() -> None:
    os.makedirs("out", exist_ok=True)

    ticks = 80

    rr_spawner = ForkBombSpawner(
        spawn_every=1,
        spawn_count=3,
        max_procs=60,
        child_demand_ms=10,
        spawn_fee_ms=SPAWN_FEE_MS,
        child_start_budget_ms=CHILD_START_BUDGET_MS,
    )

    rr_sum = run_rr_forkbomb(
        spawner=rr_spawner,
        ticks=ticks,
        jsonl_path=os.path.join("out", "forkbomb_rr.jsonl"),
        txt_path=os.path.join("out", "forkbomb_rr.txt"),
    )

    fee_values = sorted({1, SPAWN_FEE_MS, 10})
    market_results: list[dict[str, Any]] = []

    for fee in fee_values:
        spawner = ForkBombSpawner(
            spawn_every=1,
            spawn_count=3,
            max_procs=60,
            child_demand_ms=10,
            spawn_fee_ms=fee,
            child_start_budget_ms=CHILD_START_BUDGET_MS,
        )
        market_results.append(
            run_market_with_fee(
                spawner=spawner,
                ticks=ticks,
                jsonl_path=os.path.join("out", f"forkbomb_market_fee_{fee}.jsonl"),
                txt_path=os.path.join("out", f"forkbomb_market_fee_{fee}.txt"),
            )
        )

    summary_path = write_summary("out", "forkbomb_summary.json", [rr_sum] + market_results)
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    run_forkbomb_rr_and_market()