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
