from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

from amp.config import (
    DEFAULT_BUDGET_MS,
    DEFAULT_SLICE_MS,
    SPAWN_FEE_MS,
    CHILD_START_BUDGET_MS,
    MINT_RATE_ACTIVE_MS,
    MINT_RATE_THROTTLED_MS,
)


class Scenario(str, Enum):
    FORKBOMB = "forkbomb"
    CRYPTOJACKING = "cryptojacking"


class SimulationConfig(BaseModel):
    scenario: Scenario = Scenario.FORKBOMB
    ticks: int = Field(default=0, ge=0, description="0 = run until stopped")
    tick_delay_ms: int = Field(default=100, ge=10, le=2000)

    # Fork bomb params
    fork_bomb_count: int = Field(default=60, ge=1, le=120)
    spawn_fee_ms: int = Field(default=SPAWN_FEE_MS, ge=1, le=30)
    spawn_every: int = Field(default=1, ge=1, le=10)

    # Cryptojacking params
    crypto_miner_count: int = Field(default=1, ge=1, le=10)

    # Shared params
    critical_task_count: int = Field(default=1, ge=1, le=10)
    default_budget_ms: int = Field(default=DEFAULT_BUDGET_MS, ge=10, le=500)
    default_slice_ms: int = Field(default=DEFAULT_SLICE_MS, ge=1, le=50)
    mint_rate_active_ms: int = Field(default=MINT_RATE_ACTIVE_MS, ge=0, le=20)
    mint_rate_throttled_ms: int = Field(default=MINT_RATE_THROTTLED_MS, ge=0, le=20)
    child_start_budget_ms: int = Field(default=CHILD_START_BUDGET_MS, ge=1, le=100)


class ProcessSnapshot(BaseModel):
    pid: int
    name: str
    process_state: str
    execution_state: str | None = None
    budget: int | None = None
    spent: int | None = None
    last_bid: int | None = None
    cpu_share_pct: float = 0.0


class TransitionEvent(BaseModel):
    pid: int
    from_state: str
    to_state: str


class MintEvent(BaseModel):
    pid: int
    minted_ms: int
    state: str


class SchedulerTick(BaseModel):
    dispatch_pid: int | None
    granted_ms: int
    process_count: int
    processes: list[ProcessSnapshot]


class MarketSchedulerTick(SchedulerTick):
    transitions: list[TransitionEvent] = []
    mints: list[MintEvent] = []


class SystemMetrics(BaseModel):
    rr_load_pct: float = 0.0
    market_load_pct: float = 0.0
    rr_throttled_count: int = 0
    market_throttled_count: int = 0
    market_bankrupt_count: int = 0
    critical_dispatch_ratio_rr: float = 0.0
    critical_dispatch_ratio_market: float = 0.0


class TickEvent(BaseModel):
    tick: int
    scenario: str
    rr: SchedulerTick
    market: MarketSchedulerTick
    system: SystemMetrics


class SimulationStatus(BaseModel):
    session_id: str
    status: str
    tick: int = 0
    scenario: str = ""
