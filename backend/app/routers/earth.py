"""Earthquakes, wildfires, volcanoes REST endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.core.state import state
from app.models.schemas import Earthquake, Volcano, Wildfire

router = APIRouter(prefix="/api/earth", tags=["earth"])


# ---- Earthquakes ----------------------------------------------------------


@router.get("/earthquakes", response_model=list[Earthquake])
async def list_earthquakes(
    min_mag: float = Query(0.0, ge=-2, le=10),
    hours: int = Query(168, ge=1, le=720),
    limit: int = Query(500, ge=1, le=5000),
) -> list[Earthquake]:
    """Recent earthquakes, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[Earthquake] = []
    for eq in state.earthquakes:
        if eq.time < cutoff:
            continue
        if eq.mag < min_mag:
            continue
        out.append(eq)
        if len(out) >= limit:
            break
    return out


@router.get("/earthquakes/stats")
async def earthquake_stats() -> dict:
    """Quick stats for the dashboard."""
    last24 = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = [e for e in state.earthquakes if e.time >= last24]
    return {
        "total_tracked": len(state.earthquakes),
        "last_24h_count": len(recent),
        "last_24h_max_mag": max((e.mag for e in recent), default=0),
        "last_24h_min_mag": min((e.mag for e in recent), default=0),
        "tsunami_alerts": sum(1 for e in recent if e.tsunami),
        "felt_reports": sum((e.felt or 0) for e in recent),
    }


# ---- Wildfires ------------------------------------------------------------


@router.get("/wildfires", response_model=list[Wildfire])
async def list_wildfires(
    min_frp: float = Query(0.0, ge=0),
    confidence: Optional[str] = Query(None, pattern="^(low|nominal|high)$"),
    satellite: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=10000),
) -> list[Wildfire]:
    """Active fire detections, newest first."""
    out: list[Wildfire] = []
    for fire in state.wildfires:
        if fire.frp_mw < min_frp:
            continue
        if confidence and fire.confidence != confidence:
            continue
        if satellite and fire.satellite != satellite:
            continue
        out.append(fire)
        if len(out) >= limit:
            break
    return out


@router.get("/wildfires/stats")
async def wildfire_stats() -> dict:
    """Quick stats for the dashboard."""
    out = {
        "total": len(state.wildfires),
        "by_confidence": {"low": 0, "nominal": 0, "high": 0},
        "by_satellite": {},
        "total_frp_mw": 0.0,
        "max_frp_mw": 0.0,
    }
    for fire in state.wildfires:
        out["by_confidence"][fire.confidence] += 1
        out["by_satellite"][fire.satellite] = out["by_satellite"].get(fire.satellite, 0) + 1
        out["total_frp_mw"] += fire.frp_mw
        if fire.frp_mw > out["max_frp_mw"]:
            out["max_frp_mw"] = fire.frp_mw
    return out


# ---- Volcanoes ------------------------------------------------------------


@router.get("/volcanoes", response_model=list[Volcano])
async def list_volcanoes(
    level: Optional[str] = Query(None, pattern="^(unknown|normal|elevated|erupting)$"),
) -> list[Volcano]:
    """Volcanoes, optionally filtered by activity level."""
    if level is None:
        return state.volcanoes
    return [v for v in state.volcanoes if v.activity_level == level]


@router.get("/volcanoes/stats")
async def volcano_stats() -> dict:
    return {
        "total": len(state.volcanoes),
        "erupting": sum(1 for v in state.volcanoes if v.activity_level == "erupting"),
        "elevated": sum(1 for v in state.volcanoes if v.activity_level == "elevated"),
        "normal": sum(1 for v in state.volcanoes if v.activity_level == "normal"),
    }
