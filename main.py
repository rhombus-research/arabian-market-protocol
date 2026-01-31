from amp.config import DEFAULT_BUDGET_MS, DEFAULT_SLICE_MS
from amp.juno import ExecutionState, JunoRecord
from amp.process import Process
from amp.scheduler import MarketScheduler, RoundRobinScheduler
from amp.workloads import BurstDemand, ConstantDemand


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


def main() -> None:
    procs = [
        Process(pid=1, name="critical-burst", demand=BurstDemand(burst_ms=10, period=10, duty=2)),
        Process(pid=2, name="benign", demand=ConstantDemand(ms=3)),
        Process(pid=3, name="cpu-hog", demand=ConstantDemand(ms=10)),
    ]

    run_rr(procs)
    run_market(procs)


if __name__ == "__main__":
    main()
