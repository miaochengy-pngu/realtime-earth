"""Pydantic data models for all Realtime Earth layers.

These models are the **wire format** between the backend, the WebSocket, and
the frontend. Keep them stable; if you change a field, also update the
TypeScript interfaces in `frontend/src/types.ts` and the relevant Vue
component.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---- Base ------------------------------------------------------------------


class WireModel(BaseModel):
    """Common Pydantic config: serialize datetimes as ISO-8601 UTC strings."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


# ---- Satellites ------------------------------------------------------------


class SatellitePosition(BaseModel):
    """Computed satellite position at a point in time (lat/lon/alt)."""

    lat: float
    lon: float
    alt_km: float
    velocity_kms: float


class Satellite(WireModel):
    """A satellite we are tracking, with its TLE and current position."""

    id: str = Field(..., description="NORAD catalog ID, e.g. '25544' for ISS")
    name: str
    category: Literal[
        "stations",  # crewed stations (ISS, Tiangong, ...)
        "starlink",
        "hubble",
        "webb",
        "scientific",
        "weather",
        "amateur",
        "other",
    ] = "other"
    line1: str
    line2: str
    epoch: datetime
    position: Optional[SatellitePosition] = None
    intl_designator: Optional[str] = None
    launched: Optional[str] = None


# ---- Lightning -------------------------------------------------------------


class LightningStrike(WireModel):
    """A single lightning event from the Blitzortung community network."""

    id: str
    time: datetime
    lat: float
    lon: float
    alt_km: float = 0.0
    polarity: Literal["positive", "negative", "unknown"] = "unknown"
    amplitude_ka: Optional[float] = None
    strike_type: Literal["cg", "cc", "ic", "unknown"] = "unknown"
    region: Optional[str] = None


# ---- Earthquakes -----------------------------------------------------------


class Earthquake(WireModel):
    """A USGS earthquake event."""

    id: str
    mag: float
    place: str
    time: datetime
    lat: float
    lon: float
    depth_km: float
    url: str
    event_type: str = "earthquake"
    tsunami: bool = False
    felt: Optional[int] = None
    alert: Optional[Literal["green", "yellow", "orange", "red"]] = None
    significance: Optional[int] = None
    mmi: Optional[float] = None  # max reported intensity


# ---- Wildfires -------------------------------------------------------------


class Wildfire(WireModel):
    """A NASA FIRMS active fire / thermal anomaly detection."""

    id: str
    lat: float
    lon: float
    brightness_k: float
    scan_km: float
    track_km: float
    acq_date: str  # YYYY-MM-DD
    acq_time: str  # HHMM (UTC)
    acq_datetime: datetime
    satellite: str  # "NOAA-20" | "Suomi-NPP" | "NOAA-21" | "Terra" | "Aqua"
    instrument: str  # "VIIRS" | "MODIS"
    confidence: Literal["low", "nominal", "high"] = "nominal"
    frp_mw: float = 0.0  # fire radiative power, MW
    daynight: Literal["D", "N"] = "D"
    bright_ti4: Optional[float] = None
    bright_ti5: Optional[float] = None


# ---- Volcanoes -------------------------------------------------------------


class Volcano(WireModel):
    """A Smithsonian GVP volcano with current activity status."""

    id: str
    name: str
    country: str
    region: str = ""
    lat: float
    lon: float
    elevation_m: int = 0
    activity_level: Literal[
        "unknown",
        "normal",
        "elevated",
        "erupting",
    ] = "unknown"
    last_known_eruption: Optional[str] = None
    last_update: Optional[datetime] = None
    vei: Optional[int] = None  # historical VEI


# ---- Solar -----------------------------------------------------------------


class SolarSnapshot(WireModel):
    """Current state of the Sun and near-Earth space weather."""

    timestamp: datetime
    kp_index: Optional[float] = None  # 0-9, geomagnetic activity
    kp_text: Optional[str] = None
    solar_wind_speed_kms: Optional[float] = None
    solar_wind_density_pcm3: Optional[float] = None
    sunspot_number: Optional[int] = None
    xray_class: Optional[str] = None  # e.g. "C2.3"
    aurora_probability_north: Optional[float] = None  # 0-1
    aurora_probability_south: Optional[float] = None
    sdo_image_url: Optional[str] = None
    sdo_image_timestamp: Optional[datetime] = None


# ---- Health / meta ---------------------------------------------------------


class SourceStatus(BaseModel):
    ok: bool
    error: Optional[str] = None
    items: int = 0
    last_updated: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    uptime_seconds: float
    sources: dict[str, SourceStatus]
    counts: dict[str, int]
