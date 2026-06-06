"""Lightning data source.

Pulls near-real-time lightning strike data from the Blitzortung community
detection network. The network is volunteer-run; access is by courtesy of
the regional station operators.

We poll several regions in parallel every ~10s and merge results into the
shared state. Strikes older than 1 hour are dropped to keep the ring buffer
fresh.

**Attribution required**: if you use this in a public deployment, keep
attribution to Blitzortung visible in your UI. See https://www.blitzortung.org/
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import ClassVar

from app.core.state import RealtimeState
from app.models.schemas import LightningStrike
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


# Blitzortung's regional JSON endpoints. Polled in parallel; the first to
# respond wins for that region. Order matters only for log clarity.
_REGIONS: dict[str, str] = {
    "europe": "https://data.blitzortung.org/Data/Protected/lightning.json",
    "northamerica": "https://data.blitzortung.org/Data/Protected/lightning-na.json",
    "southamerica": "https://data.blitzortung.org/Data/Protected/lightning-sa.json",
    "oceania": "https://data.blitzortung.org/Data/Protected/lightning-oc.json",
    "asia": "https://data.blitzortung.org/Data/Protected/lightning-as.json",
    "africa": "https://data.blitzortung.org/Data/Protected/lightning-af.json",
}

# Blitzortung records:
#   [timestamp_seconds_float, lat, lon, altitude_m, polarity, ?]
#   The "?" field carries a coarse region hint and amplitude.
# We use a 1-hour rolling window.


class LightningSource(BaseSource):
    """Polls Blitzortung regions and appends strikes to the shared ring buffer."""

    name: ClassVar[str] = "lightning"

    def __init__(self, state: RealtimeState) -> None:
        super().__init__(state, timeout=15)
        self._last_seen_ts: dict[str, float] = {}  # region -> max strike time

    async def update(self) -> None:
        client = await self._get_client()
        new_strikes: list[LightningStrike] = []
        now = datetime.now(timezone.utc)
        max_age = now - timedelta(hours=1)
        auth_failure_regions: set[str] = set()

        for region, url in _REGIONS.items():
            try:
                resp = await client.get(url, timeout=10)
                if resp.status_code == 401 or resp.status_code == 403:
                    auth_failure_regions.add(region)
                    continue
                if resp.status_code != 200:
                    continue
                arr = resp.json()
                if not isinstance(arr, list):
                    continue

                for entry in arr:
                    try:
                        ts, lat, lon, alt_m, polarity = entry[:5]
                    except (ValueError, TypeError):
                        continue
                    strike_dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                    if strike_dt < max_age:
                        continue
                    amplitude = float(entry[7]) if len(entry) > 7 and entry[7] is not None else None
                    sid = hashlib.sha1(
                        f"{ts}-{lat}-{lon}-{alt_m}-{polarity}".encode()
                    ).hexdigest()[:16]
                    new_strikes.append(
                        LightningStrike(
                            id=sid,
                            time=strike_dt,
                            lat=float(lat),
                            lon=float(lon),
                            alt_km=float(alt_m) / 1000.0,
                            polarity="positive" if polarity > 0 else "negative" if polarity < 0 else "unknown",
                            amplitude_ka=amplitude,
                            strike_type="unknown",
                            region=region,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.debug("lightning.region_failed", extra={"region": region, "err": str(exc)})
                continue

        if auth_failure_regions and not new_strikes:
            # Blitzortung is now access-controlled; many endpoints return 401.
            # Don't mark this as an error — the source is just empty until
            # credentials are provided.
            if not auth_failure_regions < set(_REGIONS.keys()):
                logger.info(
                    "lightning.all_regions_auth",
                    extra={"auth_regions": sorted(auth_failure_regions)},
                )
            await self.state.mark_ok(self.name, len(self.state.lightning))
            return

        if not new_strikes:
            # Don't mark error — some regions are sometimes empty.
            await self.state.mark_ok(self.name, len(self.state.lightning))
            return

        # De-duplicate by id, append new ones to the ring buffer.
        existing_ids = {s.id for s in self.state.lightning}
        appended = 0
        for strike in new_strikes:
            if strike.id in existing_ids:
                continue
            self.state.lightning.append(strike)
            existing_ids.add(strike.id)
            appended += 1

        # Drop anything older than 1 hour.
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        while self.state.lightning and self.state.lightning[0].time < cutoff:
            self.state.lightning.popleft()

        await self.state.mark_ok(self.name, len(self.state.lightning))
        logger.debug("lightning.appended", extra={"appended": appended, "total": len(self.state.lightning)})
