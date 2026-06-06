"""Global in-memory state for Realtime Earth.

This module holds the latest snapshot from every enabled source. It is updated
by the APScheduler background jobs (see `app.core.scheduler`) and read by the
REST + WebSocket endpoints.

We deliberately keep state in memory and ship the latest snapshot over
WebSocket — the goal is "now", not history. Persistent storage is out of scope.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Any

from app.models.schemas import (
    Earthquake,
    LightningStrike,
    Satellite,
    SolarSnapshot,
    Volcano,
    Wildfire,
)


class RealtimeState:
    """Thread-safe (asyncio-safe) container for the latest data snapshots."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_updated: dict[str, datetime | None] = {
            "satellites": None,
            "lightning": None,
            "earthquakes": None,
            "wildfires": None,
            "volcanoes": None,
            "solar": None,
        }
        # Satellites: keyed by NORAD ID.
        self.satellites: dict[str, Satellite] = {}
        # Cached TLE lines per satellite — we re-read CelesTrak periodically.
        self.tle_cache: dict[str, tuple[str, str]] = {}

        # Ring buffers for fast-arriving data.
        self.lightning: deque[LightningStrike] = deque(maxlen=5000)
        self.earthquakes: list[Earthquake] = []
        self.wildfires: list[Wildfire] = []

        # Snapshots (single object).
        self.volcanoes: list[Volcano] = []
        self.solar: SolarSnapshot | None = None

        # Per-source status for the dashboard.
        self.status: dict[str, dict[str, Any]] = {
            "satellites": {"ok": False, "error": None, "items": 0},
            "lightning": {"ok": False, "error": None, "items": 0},
            "earthquakes": {"ok": False, "error": None, "items": 0},
            "wildfires": {"ok": False, "error": None, "items": 0},
            "volcanoes": {"ok": False, "error": None, "items": 0},
            "solar": {"ok": False, "error": None, "items": 0},
        }

    async def mark_ok(self, source: str, items: int) -> None:
        async with self._lock:
            self._last_updated[source] = datetime.utcnow()
            self.status[source] = {"ok": True, "error": None, "items": items}

    async def mark_error(self, source: str, exc: BaseException) -> None:
        async with self._lock:
            self.status[source] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "items": self.status[source].get("items", 0),
            }

    def last_updated(self, source: str) -> datetime | None:
        return self._last_updated.get(source)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot for the dashboard."""
        return {
            "last_updated": {
                k: v.isoformat() + "Z" if v else None
                for k, v in self._last_updated.items()
            },
            "status": self.status,
            "counts": {
                "satellites": len(self.satellites),
                "lightning": len(self.lightning),
                "earthquakes": len(self.earthquakes),
                "wildfires": len(self.wildfires),
                "volcanoes": len(self.volcanoes),
            },
        }


state = RealtimeState()
