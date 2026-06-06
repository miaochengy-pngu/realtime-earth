"""Health and metadata endpoints."""

from __future__ import annotations

import time
from typing import ClassVar

from fastapi import APIRouter

from app import __version__
from app.core.state import state
from app.models.schemas import HealthResponse, SourceStatus

router = APIRouter(tags=["meta"])

_BOOT_TIME = time.time()


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness/readiness — used by Docker and the frontend status panel."""
    snap = state.snapshot()
    sources: dict[str, SourceStatus] = {}
    for name, s in snap["status"].items():
        sources[name] = SourceStatus(
            ok=bool(s.get("ok")),
            error=s.get("error"),
            items=int(s.get("items", 0)),
            last_updated=state.last_updated(name),
        )
    ok_count = sum(1 for s in sources.values() if s.ok)
    return HealthResponse(
        status="ok" if ok_count == len(sources) else "degraded",
        version=__version__,
        uptime_seconds=time.time() - _BOOT_TIME,
        sources=sources,
        counts=snap["counts"],
    )


@router.get("/api/meta")
async def meta() -> dict:
    """Snapshot of the system state — used by the frontend on load."""
    return state.snapshot()
