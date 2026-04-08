from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.routes import sessions

router = APIRouter()


@router.websocket("/ws/simulation/{session_id}")
async def simulation_ws(websocket: WebSocket, session_id: str):
    engine = sessions.get(session_id)
    if engine is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        async for event in engine.tick_loop():
            payload = event.model_dump()
            await websocket.send_json(payload)

            # Check for client messages (non-blocking)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.001)
                data = json.loads(msg)
                if data.get("action") == "pause":
                    engine.paused = True
                elif data.get("action") == "resume":
                    engine.paused = False
                elif data.get("action") == "speed":
                    engine.set_speed(data.get("tick_delay_ms", 100))
                elif data.get("action") == "tune":
                    engine.tune(data)
                elif data.get("action") == "stop":
                    engine.stop()
                    break
            except (asyncio.TimeoutError, Exception):
                pass

        # Simulation ended naturally
        await websocket.send_json({"type": "complete", "tick": engine.tick})

    except WebSocketDisconnect:
        engine.stop()
    finally:
        # Clean up session
        if session_id in sessions:
            del sessions[session_id]
