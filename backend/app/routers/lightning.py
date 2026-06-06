"""Lightning REST endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.core.state import state
from app.models.schemas import LightningStrike

router = APIRouter(prefix="/api/lightning", tags=["lightning"])


@router.get("", response_model=list[LightningStrike])
async def list_lightning(
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    region: Optional[str] = Query(None, description="Blitzortung region"),
    min_amplitude_ka: Optional[float] = Query(None, ge=0),
    limit: int = Query(2000, ge=1, le=10000),
) -> list[LightningStrike]:
    """List recent lightning strikes, newest first."""
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(minutes=10)

    out: list[LightningStrike] = []
    for strike in reversed(state.lightning):
        if strike.time < since:
            continue
        if until and strike.time > until:
            continue
        if region and strike.region != region:
            continue
        if min_amplitude_ka is not None:
            if strike.amplitude_ka is None or strike.amplitude_ka < min_amplitude_ka:
                continue
        out.append(strike)
        if len(out) >= limit:
            break
    return out


@router.get("/stats")
async def lightning_stats(window_minutes: int = Query(60, ge=1, le=1440)) -> dict:
    """Aggregate counts and intensity buckets over a time window."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    recent = [s for s in state.lightning if s.time >= cutoff]
    pos = sum(1 for s in recent if s.polarity == "positive")
    neg = sum(1 for s in recent if s.polarity == "negative")
    return {
        "window_minutes": window_minutes,
        "total": len(recent),
        "positive": pos,
        "negative": neg,
        "unknown": len(recent) - pos - neg,
        "per_minute": round(len(recent) / max(window_minutes, 1), 2),
        "max_amplitude_ka": max((s.amplitude_ka or 0) for s in recent) if recent else 0,
    }
