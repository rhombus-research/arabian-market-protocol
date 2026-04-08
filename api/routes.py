from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from amp.config import (
    DEFAULT_BUDGET_MS,
    DEFAULT_SLICE_MS,
    SPAWN_FEE_MS,
    CHILD_START_BUDGET_MS,
    MINT_RATE_ACTIVE_MS,
    MINT_RATE_THROTTLED_MS,
    THROTTLE_AT_MS,
    THROTTLE_PENALTY_NUM,
    THROTTLE_PENALTY_DEN,
)
from api.models import SimulationConfig, SimulationStatus
from api.simulation import SimulationEngine

router = APIRouter(prefix="/api")

# Active sessions
sessions: dict[str, SimulationEngine] = {}
MAX_SESSIONS = 3


@router.get("/config")
def get_config():
    return {
        "default_budget_ms": DEFAULT_BUDGET_MS,
        "default_slice_ms": DEFAULT_SLICE_MS,
        "spawn_fee_ms": SPAWN_FEE_MS,
        "child_start_budget_ms": CHILD_START_BUDGET_MS,
        "mint_rate_active_ms": MINT_RATE_ACTIVE_MS,
        "mint_rate_throttled_ms": MINT_RATE_THROTTLED_MS,
        "throttle_at_ms": THROTTLE_AT_MS,
        "throttle_penalty": f"{THROTTLE_PENALTY_NUM}/{THROTTLE_PENALTY_DEN}",
    }


@router.post("/simulation/start")
def start_simulation(config: SimulationConfig) -> SimulationStatus:
    if len(sessions) >= MAX_SESSIONS:
        raise HTTPException(status_code=429, detail="Too many active sessions")

    session_id = str(uuid.uuid4())[:8]
    engine = SimulationEngine(config)
    sessions[session_id] = engine

    return SimulationStatus(
        session_id=session_id,
        status="created",
        scenario=config.scenario.value,
    )


@router.post("/simulation/stop/{session_id}")
def stop_simulation(session_id: str) -> SimulationStatus:
    engine = sessions.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Session not found")

    engine.stop()
    tick = engine.tick
    del sessions[session_id]

    return SimulationStatus(
        session_id=session_id,
        status="stopped",
        tick=tick,
    )


@router.post("/simulation/speed/{session_id}")
def set_speed(session_id: str, tick_delay_ms: int) -> dict:
    engine = sessions.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Session not found")

    engine.set_speed(tick_delay_ms)
    return {"session_id": session_id, "tick_delay_ms": engine.config.tick_delay_ms}
