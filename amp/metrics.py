from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MetricsRecorder:
    run_name: str
    out_dir: str = "out"
    _events: list[dict[str, Any]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        os.makedirs(self.out_dir, exist_ok=True)

    def add(self, event: dict[str, Any]) -> None:
        self._events.append(event)

    def write_jsonl(self, filename: str) -> str:
        path = os.path.join(self.out_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            for e in self._events:
                f.write(json.dumps(e, separators=(",", ":"), ensure_ascii=False))
                f.write("\n")
        return path

    def summary(self) -> dict[str, Any]:
        events = self._events
        if not events:
            return {"run_name": self.run_name, "event_count": 0}

        dispatches = [e for e in events if e.get("dispatch_pid") is not None]
        event_count = len(events)
        dispatch_count = len(dispatches)

        max_procs = 0
        for e in events:
            p = e.get("procs")
            if isinstance(p, int) and p > max_procs:
                max_procs = p

        grants_by_pid: dict[str, list[int]] = {}
        ticks_by_pid: dict[str, list[int]] = {}

        for e in dispatches:
            pid = str(e["dispatch_pid"])
            grant = int(e.get("granted_ms", 0))
            tick = int(e.get("tick", 0))
            grants_by_pid.setdefault(pid, []).append(grant)
            ticks_by_pid.setdefault(pid, []).append(tick)

        fairness = _fairness_index(grants_by_pid)

        return {
            "run_name": self.run_name,
            "event_count": event_count,
            "dispatch_count": dispatch_count,
            "max_procs": max_procs,
            "fairness_jain_index": fairness,
        }


def write_summary(out_dir: str, filename: str, summaries: list[dict[str, Any]]) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    payload = {"summaries": summaries}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def _fairness_index(grants_by_pid: dict[str, list[int]]) -> float:
    totals = [sum(v) for v in grants_by_pid.values() if v]
    if not totals:
        return 0.0
    s = sum(totals)
    ss = sum(t * t for t in totals)
    n = len(totals)
    if ss == 0:
        return 0.0
    return (s * s) / (n * ss)


def compute_bankruptcy_tick(events: list[dict[str, Any]], pid: int) -> int | None:
    pid_s = str(pid)
    for e in events:
        if str(e.get("dispatch_pid")) != pid_s and str(e.get("pid")) != pid_s:
            continue
        if e.get("state_after") == "BANKRUPT":
            return int(e.get("tick", 0))
    return None


def critical_responsiveness(events: list[dict[str, Any]], critical_pid: int) -> dict[str, Any]:
    crit = str(critical_pid)
    ticks = [int(e["tick"]) for e in events if str(e.get("dispatch_pid")) == crit]
    if not ticks:
        return {"critical_pid": critical_pid, "runs": 0}

    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    max_gap = max(gaps) if gaps else 0
    mean_gap = (sum(gaps) / len(gaps)) if gaps else 0.0

    return {
        "critical_pid": critical_pid,
        "runs": len(ticks),
        "first_tick": ticks[0],
        "last_tick": ticks[-1],
        "max_gap_ticks": max_gap,
        "mean_gap_ticks": mean_gap,
    }
