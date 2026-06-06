"""NASA FIRMS active-fire / thermal-anomaly source.

NASA's Fire Information for Resource Management System publishes near-real-time
thermal anomaly detections from VIIRS and MODIS. The 24-hour global CSV is
free to download without authentication; a free MAP_KEY raises the rate limit.

Reference: https://firms.modaps.eosdis.nasa.gov/api/
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import ClassVar

from app.core.config import get_settings
from app.core.state import RealtimeState
from app.models.schemas import Wildfire
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


# We use the 24-hour global VIIRS feed (NOAA-20 J1 and S-NPP).
# These URLs are publicly accessible without authentication.
# A free MAP_KEY (from https://firms.modaps.eosdis.nasa.gov/api/) raises the
# rate limit when present; it's optional.
FIRMS_VIIRS_FEEDS = [
    # NOAA-20 (J1)
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/c2/csv/J1_VIIRS_C2_Global_24h.csv",
    # S-NPP
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
    # NOAA-21 (J2)
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/c2/csv/J2_VIIRS_C2_Global_24h.csv",
]


class WildfiresSource(BaseSource):
    """NASA FIRMS VIIRS + MODIS thermal anomalies."""

    name: ClassVar[str] = "wildfires"

    async def update(self) -> None:
        settings = get_settings()
        key = settings.firms_map_key

        all_rows: list[Wildfire] = []
        for base in FIRMS_VIIRS_FEEDS:
            url = f"{base}?MAP_KEY={key}" if key else base
            try:
                text = await self.safe_get_text(url, timeout=60)
                all_rows.extend(_parse_firms_csv(text))
            except Exception as exc:  # noqa: BLE001
                logger.warning("firms.fetch_failed", extra={"url": url, "err": str(exc)})

        if not all_rows:
            raise RuntimeError("FIRMS feed returned no rows")

        # Cap & dedupe by (lat, lon, time, satellite)
        cap = settings.max_wildfires
        seen: set[tuple] = set()
        unique: list[Wildfire] = []
        for w in all_rows:
            key_t = (round(w.lat, 3), round(w.lon, 3), w.acq_datetime, w.satellite)
            if key_t in seen:
                continue
            seen.add(key_t)
            unique.append(w)
            if len(unique) >= cap:
                break

        self.state.wildfires = unique
        await self.state.mark_ok(self.name, len(unique))


def _parse_firms_csv(text: str) -> list[Wildfire]:
    """Parse a FIRMS CSV (lat, lon, brightness, scan, track, acq_date, acq_time, ...)."""
    out: list[Wildfire] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            # FIRMS CSVs use bright_ti4 (or bright_ti5 for I-band); fall back
            # to either if one is missing.
            try:
                brightness = float(row.get("bright_ti4") or row.get("bright_ti5") or 0)
            except ValueError:
                brightness = 0.0
            scan = float(row.get("scan", 0) or 0)
            track = float(row.get("track", 0) or 0)
            date = row.get("acq_date", "")
            time_ = row.get("acq_time", "")
            satellite = row.get("satellite", "Unknown")
            instrument = row.get("instrument", "VIIRS")
            confidence = (row.get("confidence") or "nominal").lower()
            if confidence not in ("low", "nominal", "high"):
                confidence = "nominal"
            try:
                frp = float(row.get("frp", 0) or 0)
            except ValueError:
                frp = 0.0
            daynight = (row.get("daynight") or "D").upper()
            if daynight not in ("D", "N"):
                daynight = "D"

            # Build acq_datetime
            try:
                if len(time_) == 4:
                    hh, mm = int(time_[:2]), int(time_[2:4])
                else:
                    hh, mm = 0, 0
                acq_dt = datetime.strptime(date, "%Y-%m-%d").replace(
                    hour=hh, minute=mm, tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                acq_dt = datetime.now(timezone.utc)

            wid = f"{satellite}-{date}-{time_}-{round(lat, 3)}-{round(lon, 3)}"
            try:
                bright_ti4 = float(row["bright_ti4"]) if row.get("bright_ti4") else None
            except ValueError:
                bright_ti4 = None
            try:
                bright_ti5 = float(row["bright_ti5"]) if row.get("bright_ti5") else None
            except ValueError:
                bright_ti5 = None

            out.append(
                Wildfire(
                    id=wid,
                    lat=lat,
                    lon=lon,
                    brightness_k=brightness,
                    scan_km=scan,
                    track_km=track,
                    acq_date=date,
                    acq_time=time_,
                    acq_datetime=acq_dt,
                    satellite=satellite,
                    instrument=instrument,
                    confidence=confidence,  # type: ignore[arg-type]
                    frp_mw=frp,
                    daynight=daynight,  # type: ignore[arg-type]
                    bright_ti4=bright_ti4,
                    bright_ti5=bright_ti5,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("firms.row_failed", extra={"err": str(exc)})
            continue
    return out
