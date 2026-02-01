from amp.config import CHILD_START_BUDGET_MS, DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS, SPAWN_FEE_MS
from amp.juno import ExecutionState, JunoRecord
from amp.process import Process
from amp.scheduler import MarketScheduler, RoundRobinScheduler
from amp.workloads import BurstDemand, ConstantDemand
from amp.workloads import ForkBombSpawner

import os


def run_rr(procs: list[Process]) -> None:
    print("\n=== Round Robin ===")
    sched = RoundRobinScheduler()
    for tick in range(30):
        d = sched.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        print(f"tick={tick:02d} dispatch pid={d.pid} grant_ms={d.granted_ms}")


def run_market(procs: list[Process]) -> None:
    print("\n=== Market ===")
    records = {
        p.pid: JunoRecord(
            pid=p.pid,
            budget=DEFAULT_BUDGET_MS,
            spent=0,
            state=ExecutionState.ACTIVE,
            last_bid=0,
        )
        for p in procs
    }

    sched = MarketScheduler(records)

    for tick in range(30):
        d = sched.select(procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
        r = records.get(d.pid) if d.pid is not None else None
        if r is None:
            print(f"tick={tick:02d} dispatch pid=None grant_ms=0")
        else:
            print(
                f"tick={tick:02d} dispatch pid={d.pid} grant_ms={d.granted_ms} "
                f"budget={r.budget} state={r.state.name} last_bid={r.last_bid}"
            )


# def main() -> None:
#     procs = [
#         Process(pid=1, name="critical-burst", demand=BurstDemand(burst_ms=10, period=10, duty=2)),
#         Process(pid=2, name="benign", demand=ConstantDemand(ms=3)),
#         Process(pid=3, name="cpu-hog", demand=ConstantDemand(ms=10)),
#     ]
#
#     run_rr(procs)
#     run_market(procs)

# def run_forkbomb_rr_and_market() -> None:
#     ticks = 50
#     spawner = ForkBombSpawner(
#         spawn_every=1,
#         spawn_count=3,
#         max_procs=60,
#         child_demand_ms=10,
#     )
#
#     base = [
#         Process(pid=1, name="critical-burst", demand=BurstDemand(burst_ms=10, period=10, duty=2)),
#         Process(pid=2, name="benign", demand=ConstantDemand(ms=3)),
#         Process(pid=3, name="attacker-root", demand=ConstantDemand(ms=10)),
#     ]
#
#     rr_procs = list(base)
#     market_procs = list(base)
#
#     print("\n=== Round Robin (Fork Bomb) ===")
#     rr = RoundRobinScheduler()
#     for tick in range(ticks):
#         to_spawn = spawner.new_children(tick=tick, current_total=len(rr_procs))
#         for _ in range(to_spawn):
#             new_pid = max(p.pid for p in rr_procs) + 1
#             rr_procs.append(Process(pid=new_pid, name=f"attacker-{new_pid}", demand=ConstantDemand(ms=10)))
#
#         d = rr.select(rr_procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
#         print(f"tick={tick:02d} procs={len(rr_procs):02d} dispatch pid={d.pid} grant_ms={d.granted_ms}")
#
#     print("\n=== Market (Fork Bomb) ===")
#     records = {
#         p.pid: JunoRecord(
#             pid=p.pid,
#             budget=DEFAULT_BUDGET_MS,
#             spent=0,
#             state=ExecutionState.ACTIVE,
#             last_bid=0,
#         )
#         for p in market_procs
#     }
#     market = MarketScheduler(records)
#
#     for tick in range(ticks):
#         to_spawn = spawner.new_children(tick=tick, current_total=len(market_procs))
#         for _ in range(to_spawn):
#             new_pid = max(p.pid for p in market_procs) + 1
#             market_procs.append(Process(pid=new_pid, name=f"attacker-{new_pid}", demand=ConstantDemand(ms=10)))
#             records[new_pid] = JunoRecord(
#                 pid=new_pid,
#                 budget=DEFAULT_BUDGET_MS,
#                 spent=0,
#                 state=ExecutionState.ACTIVE,
#                 last_bid=0,
#             )
#
#         d = market.select(market_procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
#         if d.pid is None:
#             print(f"tick={tick:02d} procs={len(market_procs):02d} dispatch pid=None grant_ms=0")
#         else:
#             r = records[d.pid]
#             print(
#                 f"tick={tick:02d} procs={len(market_procs):02d} dispatch pid={d.pid} grant_ms={d.granted_ms} "
#                 f"budget={r.budget} state={r.state.name}"
#             )


def run_forkbomb_rr_and_market() -> None:
    os.makedirs("out", exist_ok=True)

    rr_path = os.path.join("out", "forkbomb_rr.txt")
    market_path = os.path.join("out", "forkbomb_market.txt")

    ticks = 80
    spawner = ForkBombSpawner(
        spawn_every=1,
        spawn_count=3,
        max_procs=60,
        child_demand_ms=10,
        spawn_fee_ms=SPAWN_FEE_MS,
        child_start_budget_ms=CHILD_START_BUDGET_MS,
    )

    base = [
        Process(pid=1, name="critical-burst", demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=2, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=3, name="attacker-root", demand=ConstantDemand(ms=10)),
    ]

    rr_procs = list(base)
    market_procs = list(base)

    with open(rr_path, "w", encoding="utf-8") as rr_out:
        rr_out.write("=== Round Robin (Fork Bomb) ===\n")
        rr = RoundRobinScheduler()

        for tick in range(ticks):
            to_spawn = spawner.new_children(tick=tick, current_total=len(rr_procs))
            for _ in range(to_spawn):
                new_pid = max(p.pid for p in rr_procs) + 1
                rr_procs.append(Process(pid=new_pid, name=f"attacker-{new_pid}", demand=ConstantDemand(ms=10)))

            d = rr.select(rr_procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)
            rr_out.write(f"tick={tick:02d} procs={len(rr_procs):02d} dispatch pid={d.pid} grant_ms={d.granted_ms}\n")

    with open(market_path, "w", encoding="utf-8") as m_out:
        m_out.write("=== Market (Fork Bomb) ===\n")

        records = {
            p.pid: JunoRecord(
                pid=p.pid,
                budget=DEFAULT_BUDGET_MS,
                spent=0,
                state=ExecutionState.ACTIVE,
                last_bid=0,
            )
            for p in market_procs
        }

        market = MarketScheduler(records)

        attacker_root_pid = 3

        for tick in range(ticks):
            # Spawn economics:
            # - New children are not minted with full DEFAULT_BUDGET_MS
            # - Root attacker pays a spawn fee per child
            # - Each child starts with a small budget (child_start_budget_ms)
            root = records[attacker_root_pid]

            desired = spawner.new_children(tick=tick, current_total=len(market_procs))
            affordable = 0

            if root.state is not ExecutionState.BANKRUPT and root.budget > 0:
                max_affordable = root.budget // spawner.spawn_fee_ms if spawner.spawn_fee_ms > 0 else desired
                affordable = desired if desired <= max_affordable else max_affordable

            for _ in range(affordable):
                root.budget -= spawner.spawn_fee_ms
                root.spent += spawner.spawn_fee_ms
                if root.budget <= 0:
                    root.budget = 0
                    root.state = ExecutionState.BANKRUPT
                    break

                new_pid = max(p.pid for p in market_procs) + 1
                market_procs.append(Process(pid=new_pid, name=f"attacker-{new_pid}", demand=ConstantDemand(ms=10)))
                records[new_pid] = JunoRecord(
                    pid=new_pid,
                    budget=spawner.child_start_budget_ms,
                    spent=0,
                    state=ExecutionState.ACTIVE,
                    last_bid=0,
                )

            d = market.select(market_procs, tick=tick, slice_ms=DEFAULT_SLICE_MS)

            if d.pid is None:
                m_out.write(f"tick={tick:02d} procs={len(market_procs):02d} dispatch pid=None grant_ms=0\n")
            else:
                r = records[d.pid]
                m_out.write(
                    f"tick={tick:02d} procs={len(market_procs):02d} dispatch pid={d.pid} grant_ms={d.granted_ms} "
                    f"budget={r.budget} state={r.state.name}\n"
                )

        m_out.write("\n=== Summary ===\n")
        bankrupt = sum(1 for r in records.values() if r.state is ExecutionState.BANKRUPT)
        m_out.write(f"total_procs={len(market_procs)} bankrupt={bankrupt}\n")
        m_out.write(f"attacker_root_budget={records[attacker_root_pid].budget} state={records[attacker_root_pid].state.name}\n")

def main() -> None:
    run_forkbomb_rr_and_market()

if __name__ == "__main__":
    main()
