"""Satellite REST endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.core.state import state
from app.models.schemas import Satellite

router = APIRouter(prefix="/api/satellites", tags=["satellites"])


@router.get("", response_model=list[Satellite])
async def list_satellites(
    category: Optional[str] = Query(None, description="Filter by category"),
    q: Optional[str] = Query(None, description="Substring match on name"),
    limit: int = Query(500, ge=1, le=5000),
) -> list[Satellite]:
    """List all tracked satellites, with optional category/text filters."""
    sats = list(state.satellites.values())
    if category:
        sats = [s for s in sats if s.category == category]
    if q:
        ql = q.lower()
        sats = [s for s in sats if ql in s.name.lower()]
    return sats[:limit]


@router.get("/prominent", response_model=list[Satellite])
async def prominent_satellites() -> list[Satellite]:
    """The 'headline' satellites — ISS, Tiangong, Hubble, Webb."""
    headliners = ["ISS (ZARYA)", "TIANGONG", "HUBBLE SPACE TELESCOPE", "JAMES WEBB SPACE TELESCOPE"]
    out: list[Satellite] = []
    for sat in state.satellites.values():
        if any(h in sat.name.upper() for h in headliners):
            out.append(sat)
    return out


@router.get("/{norad_id}/position")
async def satellite_position_at(
    norad_id: str, when: Optional[datetime] = None
) -> dict:
    """Compute a satellite's position at an arbitrary UTC time.

    Uses SGP4 with the cached TLE for the given NORAD ID. If no `when` is
    provided, the current time is used.
    """
    tle = state.tle_cache.get(norad_id)
    if not tle:
        return {"error": "satellite not found"}
    line1, line2 = tle
    when = when or datetime.now(timezone.utc)
    from sgp4.api import Satrec, jday

    sat = Satrec.twoline2rv(line1, line2)
    jd, fr = jday(
        when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond / 1e6
    )
    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        return {"error": f"SGP4 error code {e}", "code": e}
    return {
        "id": norad_id,
        "when": when.isoformat(),
        "position_teme_km": list(r),
        "velocity_kms": list(v),
        "speed_kms": (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5,
    }
