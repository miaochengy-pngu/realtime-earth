"""Solar / space weather REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.state import state
from app.models.schemas import SolarSnapshot

router = APIRouter(prefix="/api/solar", tags=["solar"])


@router.get("", response_model=SolarSnapshot | None)
async def current_solar() -> SolarSnapshot | None:
    """Latest solar / space weather snapshot."""
    return state.solar


@router.get("/summary")
async def solar_summary() -> dict:
    """A human-friendly summary for the dashboard side-panel."""
    s = state.solar
    if s is None:
        return {"ready": False}
    kp = s.kp_index
    storm_level = "None"
    if kp is not None:
        if kp >= 9:
            storm_level = "G5 — Extreme"
        elif kp >= 8:
            storm_level = "G4 — Severe"
        elif kp >= 7:
            storm_level = "G3 — Strong"
        elif kp >= 6:
            storm_level = "G2 — Moderate"
        elif kp >= 5:
            storm_level = "G1 — Minor"
        elif kp >= 4:
            storm_level = "Active"
        else:
            storm_level = "Quiet"
    return {
        "ready": True,
        "kp_index": s.kp_index,
        "kp_text": s.kp_text,
        "storm_level": storm_level,
        "solar_wind_speed_kms": s.solar_wind_speed_kms,
        "solar_wind_density_pcm3": s.solar_wind_density_pcm3,
        "sunspot_number": s.sunspot_number,
        "xray_class": s.xray_class,
        "aurora_probability_north": s.aurora_probability_north,
        "aurora_probability_south": s.aurora_probability_south,
        "sdo_image_url": s.sdo_image_url,
        "timestamp": s.timestamp.isoformat() if s.timestamp else None,
    }
