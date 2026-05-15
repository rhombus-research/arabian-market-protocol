"""Baseline schedulers for comparison against AMP.

Two schedulers are provided:

  CFSScheduler   — Weighted virtual-time proportional-share. Approximates
                   Linux CFS without budgets, throttling, or spawn fees.
                   All processes start with equal weight; the runnable
                   process with the lowest vruntime is selected.

  CgroupScheduler — CFS with per-cgroup CPU quota over a fixed period.
                    Each cgroup is assigned a quota_ms per period; when
                    exhausted, all processes in that cgroup are ineligible
                    until the next period. Models a real admin-configured
                    cgroup deployment, including the misconfiguration case
                    where attacker and critical share a cgroup.

Neither scheduler maintains Sijil records, prices process creation, nor
implements economic enforcement. They serve as comparison baselines for
the AMP results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from amp.process import Process, ProcessState
from amp.scheduler import Dispatch


@dataclass(slots=True)
class _CFSEntry:
    pid: int
    weight: int
    vruntime: int = 0


class CFSScheduler:
    """Weighted virtual-time proportional-share scheduler.

    Each runnable process tracks a virtual runtime. The process with the
    lowest vruntime among runnable processes is selected. vruntime is
    incremented by `grant_ms * BASE_WEIGHT / weight`; with equal weights
    this collapses to grant_ms.

    No budget, no throttling, no spawn-fee. New processes inherit the
    minimum vruntime among current runnables to avoid unbounded scheduler
    favoritism on registration.
    """

    BASE_WEIGHT = 1024  # Linux CFS nice=0 weight

    def __init__(self) -> None:
        self._entries: dict[int, _CFSEntry] = {}

    def _ensure(self, processes: Sequence[Process]) -> None:
        # Initialize new arrivals at the current minimum vruntime so they
        # do not monopolize the CPU on registration.
        min_v = min((e.vruntime for e in self._entries.values()), default=0)
        for p in processes:
            if p.pid not in self._entries:
                self._entries[p.pid] = _CFSEntry(pid=p.pid, weight=self.BASE_WEIGHT, vruntime=min_v)

    def select(self, processes: Sequence[Process], tick: int, slice_ms: int) -> Dispatch:
        self._ensure(processes)

        best_pid: int | None = None
        best_v = 0
        best_req = 0
        for p in processes:
            if p.state is not ProcessState.RUNNABLE:
                continue
            req = p.requested_ms(tick)
            if req <= 0:
                continue
            entry = self._entries[p.pid]
            if best_pid is None or entry.vruntime < best_v:
                best_pid = p.pid
                best_v = entry.vruntime
                best_req = req

        if best_pid is None:
            return Dispatch(pid=None, granted_ms=0)

        grant = best_req if best_req < slice_ms else slice_ms
        entry = self._entries[best_pid]
        entry.vruntime += (grant * self.BASE_WEIGHT) // entry.weight
        return Dispatch(pid=best_pid, granted_ms=grant)


@dataclass(slots=True)
class CgroupConfig:
    name: str
    quota_ms: int       # ms of CPU per period
    period_ticks: int   # length of a quota period in ticks
    pids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class _CgroupState:
    config: CgroupConfig
    consumed_ms: int = 0
    period_start_tick: int = 0


class CgroupScheduler:
    """CFS with per-cgroup CPU quota enforcement.

    Each process is assigned to a cgroup. A cgroup is ineligible when its
    consumed_ms within the current period exceeds quota_ms. Consumed counters
    reset at every period boundary.

    Constructed with a mapping {pid -> cgroup_name} and a list of cgroup
    configs. Processes registered later (e.g., fork-bombed children) must
    have their cgroup assignment provided at registration time via
    register_pid(); unregistered pids are placed in a default 'unassigned'
    cgroup with quota = period_ticks * slice_ms (effectively unrestricted).
    """

    def __init__(self, cgroups: list[CgroupConfig], pid_to_cgroup: dict[int, str]) -> None:
        self._cgroups: dict[str, _CgroupState] = {c.name: _CgroupState(config=c) for c in cgroups}
        self._pid_to_cgroup: dict[int, str] = dict(pid_to_cgroup)
        for c in cgroups:
            for pid in c.pids:
                self._pid_to_cgroup[pid] = c.name
        self._cfs = CFSScheduler()

    def register_pid(self, pid: int, cgroup_name: str) -> None:
        if cgroup_name not in self._cgroups:
            raise ValueError(f"unknown cgroup {cgroup_name}")
        self._pid_to_cgroup[pid] = cgroup_name

    def _cgroup_for(self, pid: int) -> _CgroupState | None:
        name = self._pid_to_cgroup.get(pid)
        if name is None:
            return None
        return self._cgroups[name]

    def _maybe_reset_period(self, tick: int) -> None:
        for state in self._cgroups.values():
            if tick - state.period_start_tick >= state.config.period_ticks:
                state.consumed_ms = 0
                state.period_start_tick = tick

    def select(self, processes: Sequence[Process], tick: int, slice_ms: int) -> Dispatch:
        self._maybe_reset_period(tick)

        # Filter out processes whose cgroup has exhausted its quota.
        eligible: list[Process] = []
        for p in processes:
            if p.state is not ProcessState.RUNNABLE:
                continue
            cg = self._cgroup_for(p.pid)
            if cg is None:
                # Unassigned pid: allow by default (matches Linux cgroup v2 root-cgroup behavior)
                eligible.append(p)
                continue
            if cg.consumed_ms >= cg.config.quota_ms:
                continue
            eligible.append(p)

        d = self._cfs.select(eligible, tick=tick, slice_ms=slice_ms)
        if d.pid is not None and d.granted_ms > 0:
            cg = self._cgroup_for(d.pid)
            if cg is not None:
                cg.consumed_ms += d.granted_ms
        return d
