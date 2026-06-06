"""Earthquake data source.

USGS provides free, public, real-time earthquake feeds in GeoJSON. We poll
the "all_hour" feed for fresh events and the "all_week" feed once an hour to
backfill any that we missed.

Endpoints:
  * https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson
  * https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
  * https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson

The feed is updated every minute.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import ClassVar

from app.core.state import RealtimeState
from app.models.schemas import Earthquake
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

_HOUR_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
_DAY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


class EarthquakesSource(BaseSource):
    """USGS earthquake feed."""

    name: ClassVar[str] = "earthquakes"

    async def update(self) -> None:
        # The "hour" feed is small; the "day" feed gives richer history.
        features: list[dict] = []
        for url in (_HOUR_URL, _DAY_URL):
            try:
                data = await self.safe_get_json(url, timeout=15)
                features.extend(data.get("features", []))
            except Exception as exc:  # noqa: BLE001
                logger.warning("quake.fetch_failed", extra={"url": url, "err": str(exc)})

        if not features:
            raise RuntimeError("USGS feed returned no features")

        # Convert to Earthquake models, dedupe by id.
        by_id: dict[str, Earthquake] = {}
        for f in features:
            try:
                props = f.get("properties", {}) or {}
                geom = f.get("geometry", {}) or {}
                coords = geom.get("coordinates", [0, 0, 0])
                lon, lat, depth = coords[0], coords[1], coords[2]
                if lat is None or lon is None:
                    continue
                ts_ms = props.get("time")
                if ts_ms is None:
                    continue
                eq = Earthquake(
                    id=f["id"],
                    mag=float(props.get("mag", 0.0) or 0.0),
                    place=str(props.get("place", "Unknown")),
                    time=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                    lat=float(lat),
                    lon=float(lon),
                    depth_km=float(depth or 0.0),
                    url=str(props.get("detail", "")) or "https://earthquake.usgs.gov/",
                    event_type=str(props.get("type", "earthquake")),
                    tsunami=bool(props.get("tsunami", 0)),
                    felt=(int(props["felt"]) if props.get("felt") is not None else None),
                    alert=props.get("alert"),
                    significance=props.get("sig"),
                    mmi=props.get("mmi"),
                )
                by_id[eq.id] = eq
            except Exception as exc:  # noqa: BLE001
                logger.debug("quake.decode_failed", extra={"err": str(exc)})
                continue

        # Newest first, capped to max_earthquakes from settings.
        from app.core.config import get_settings

        cap = get_settings().max_earthquakes
        sorted_eqs = sorted(by_id.values(), key=lambda e: e.time, reverse=True)[:cap]
        self.state.earthquakes = sorted_eqs
        await self.state.mark_ok(self.name, len(sorted_eqs))
