"""WebSocket endpoint for real-time pushes.

The frontend connects to `/ws` and receives a `topic` field on every message.
Topics:
  * `meta`     — system health snapshot
  * `lightning` — most recent N strikes
  * `satellites` — full satellite list with positions
  * `earth`    — earthquakes + wildfires + volcanoes
  * `solar`    — solar snapshot

Send a JSON `{"subscribe": ["lightning", "satellites"]}` to choose topics;
`["*"]` or absent means subscribe to all.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, ClassVar

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import state

logger = logging.getLogger(__name__)

router = APIRouter()


_PUSH_INTERVAL = 5.0  # seconds


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    subs: set[str] = {"*"}
    try:
        await websocket.send_json({"topic": "hello", "t": time.time()})

        last_meta_t = 0.0
        last_lightning_t = 0.0
        last_satellite_t = 0.0
        last_earth_t = 0.0
        last_solar_t = 0.0

        while True:
            try:
                # Drain any inbound messages (subscription updates) without
                # blocking forever.
                inbound = await asyncio.wait_for(
                    websocket.receive_text(), timeout=_PUSH_INTERVAL
                )
            except asyncio.TimeoutError:
                inbound = None
            except WebSocketDisconnect:
                break

            if inbound:
                try:
                    msg = json.loads(inbound)
                    if isinstance(msg, dict) and "subscribe" in msg:
                        subs = set(msg["subscribe"]) or {"*"}
                        await websocket.send_json(
                            {"topic": "subscribed", "subs": sorted(subs)}
                        )
                except json.JSONDecodeError:
                    pass
                continue

            now = time.time()
            if "*" in subs or "meta" in subs:
                if now - last_meta_t >= _PUSH_INTERVAL:
                    await _safe_send(websocket, {"topic": "meta", "data": state.snapshot()})
                    last_meta_t = now

            if "*" in subs or "lightning" in subs:
                if now - last_lightning_t >= _PUSH_INTERVAL:
                    strikes = list(state.lightning)[-2000:]
                    await _safe_send(
                        websocket,
                        {"topic": "lightning", "data": [s.model_dump(mode="json") for s in strikes]},
                    )
                    last_lightning_t = now

            if "*" in subs or "satellites" in subs:
                if now - last_satellite_t >= _PUSH_INTERVAL * 2:
                    sats = [s.model_dump(mode="json") for s in state.satellites.values()]
                    await _safe_send(
                        websocket,
                        {"topic": "satellites", "data": sats},
                    )
                    last_satellite_t = now

            if "*" in subs or "earth" in subs:
                if now - last_earth_t >= _PUSH_INTERVAL * 2:
                    payload = {
                        "earthquakes": [e.model_dump(mode="json") for e in state.earthquakes[:500]],
                        "wildfires": [w.model_dump(mode="json") for w in state.wildfires[:2000]],
                        "volcanoes": [v.model_dump(mode="json") for v in state.volcanoes],
                    }
                    await _safe_send(websocket, {"topic": "earth", "data": payload})
                    last_earth_t = now

            if "*" in subs or "solar" in subs:
                if now - last_solar_t >= _PUSH_INTERVAL:
                    s = state.solar
                    if s is not None:
                        await _safe_send(
                            websocket,
                            {"topic": "solar", "data": s.model_dump(mode="json")},
                        )
                    last_solar_t = now

    except WebSocketDisconnect:
        logger.info("ws.client_disconnected")
    except Exception as exc:  # noqa: BLE001
        logger.exception("ws.error", extra={"err": str(exc)})
    finally:
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass


async def _safe_send(websocket: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await websocket.send_json(payload)
    except Exception:  # noqa: BLE001
        # Client likely disconnected; let outer loop handle it.
        raise
