from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConstantDemand:
    ms: int

    def demand_ms(self, tick: int) -> int:
        return self.ms


@dataclass(slots=True)
class BurstDemand:
    burst_ms: int
    period: int
    duty: int

    def demand_ms(self, tick: int) -> int:
        phase = tick % self.period
        return self.burst_ms if phase < self.duty else 0


# @dataclass(slots=True)
# class ForkBombSpawner:
#     spawn_every: int
#     spawn_count: int
#     max_procs: int
#     child_demand_ms: int
#
#     def new_children(self, tick: int, current_total: int) -> int:
#         if current_total >= self.max_procs:
#             return 0
#         if self.spawn_every <= 0:
#             return 0
#         if tick % self.spawn_every != 0:
#             return 0
#         remaining = self.max_procs - current_total
#         return self.spawn_count if self.spawn_count <= remaining else remaining

@dataclass(slots=True)
class ForkBombSpawner:
    spawn_every: int
    spawn_count: int
    max_procs: int
    child_demand_ms: int
    spawn_fee_ms: int
    child_start_budget_ms: int

    def new_children(self, tick: int, current_total: int) -> int:
        if current_total >= self.max_procs:
            return 0
        if self.spawn_every <= 0:
            return 0
        if tick % self.spawn_every != 0:
            return 0
        remaining = self.max_procs - current_total
        return self.spawn_count if self.spawn_count <= remaining else remaining