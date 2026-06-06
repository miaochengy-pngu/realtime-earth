"""Satellite data source.

Pulls Two-Line Element (TLE) sets from CelesTrak for several curated groups,
then computes the current position of each satellite using SGP4.

We track these groups (small, hand-picked — this is for visualisation, not
operational tracking):
  * `stations`     — crewed stations (ISS, Tiangong / 中国空间站, ...)
  * `weather`      — a few prominent weather sats
  * `scientific`   — a handful of science missions
  * `amateur`      — a small set of bright amateur sats

TLE data is cached to `.cache/tle.json` so the app degrades gracefully if
CelesTrak is briefly unreachable.

**CelesTrak data format note**: the JSON `gp.php` endpoint returns
*individual TLE elements* (MEAN_MOTION, ECCENTRICITY, etc.), not the two-line
text format. We use the `tle` format endpoint and parse the lines manually.

Note: The James Webb Space Telescope (JWST) operates at the Sun-Earth L2
Lagrange point, ~1.5 million km from Earth. The SGP4 model used here is for
near-Earth objects and cannot propagate an L2 orbit. We therefore **do not**
attempt to render JWST — including it would be misleading. The Hubble Space
Telescope is included (it's in LEO).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from sgp4.api import Satrec, jday

from app.core.state import RealtimeState
from app.models.schemas import Satellite, SatellitePosition
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


# Hand-picked CelesTrak groups. We skip Starlink (403 rate-limited; SGP4 also
# struggles at 7000+ entities) and similar huge catalogs.
_CELESTRAK_GROUPS: dict[str, str] = {
    "stations": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "scientific": "https://celestrak.org/NORAD/elements/gp.php?GROUP=scientific&FORMAT=tle",
    "amateur": "https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=tle",
}

# Cap each group to avoid loading thousands of objects at once
_GROUP_LIMITS: dict[str, int] = {
    "stations": 30,
    "weather": 30,
    "scientific": 30,
    "amateur": 30,
}

# Special-case TLE fetches for famous objects.
_PROMINENT: dict[str, dict[str, str]] = {
    "ISS (ZARYA)": {
        "norad": "25544",
        "url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle",
    },
    "CSS (TIANHE)": {
        "norad": "48274",
        "url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=48274&FORMAT=tle",
    },
    "HUBBLE": {
        "norad": "20580",
        "url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=20580&FORMAT=tle",
    },
}

_PROMINENT_CATEGORIES: dict[str, str] = {
    "ISS (ZARYA)": "stations",
    "CSS (TIANHE)": "stations",
    "CSS (WENTIAN)": "stations",
    "CSS (MENGTIAN)": "stations",
    "HUBBLE": "hubble",
}


def _classify(name: str) -> str:
    upper = name.upper()
    for key, cat in _PROMINENT_CATEGORIES.items():
        if key.upper() in upper:
            return cat
    if "TIANGONG" in upper or "CSS" in upper:
        return "stations"
    if "ISS" in upper or "ZARYA" in upper:
        return "stations"
    if "HUBBLE" in upper or "HST" in upper:
        return "hubble"
    if "NOAA" in upper or "METEOR" in upper or "GOES" in upper or "FENGYUN" in upper:
        return "weather"
    return "other"


def _parse_tle_text(text: str) -> list[dict[str, str]]:
    """Parse CelesTrak TLE text format.

    The TLE format is:

        ISS (ZARYA)
        1 25544U 98067A   24001.50000000  .00010000  00000-0  18000-3 0  9990
        2 25544  51.6400 100.0000 0001000  90.0000 270.0000 15.50000000400000

    Returns a list of dicts with `name`, `line1`, `line2`, `norad`, `intl_designator`.
    """
    out: list[dict[str, str]] = []
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i + 2 < len(lines):
        # Line 1: name, line 2 starts with "1 ", line 3 starts with "2 "
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()
        if line1.startswith("1 ") and line2.startswith("2 "):
            norad = line1.split()[1].rstrip("U") if len(line1.split()) > 1 else ""
            intl = line1[9:17].strip() if len(line1) > 17 else ""
            out.append(
                {
                    "name": name,
                    "line1": line1,
                    "line2": line2,
                    "norad": norad,
                    "intl_designator": intl,
                }
            )
            i += 3
        else:
            i += 1
    return out


def _parse_epoch_from_tle(line1: str) -> datetime:
    """Extract epoch from TLE line 1 (columns 19-32).

    Format: YYDDD.DDDDDDDD where YY=2-digit year, DDD=day of year.
    """
    try:
        epoch_str = line1[18:32].strip()
        yy = int(epoch_str[0:2])
        ddd = float(epoch_str[2:])
        # 2-digit year: 00-56 = 2000+, 57-99 = 1900+
        year = 2000 + yy if yy < 57 else 1900 + yy
        # Day of year
        base = datetime(year, 1, 1, tzinfo=timezone.utc)
        delta = timedelta(days=ddd - 1)
        return base + delta
    except (ValueError, IndexError):
        return datetime.now(timezone.utc)


from datetime import timedelta  # noqa: E402  (after _parse_epoch_from_tle)


class SatellitesSource(BaseSource):
    """Fetches TLEs and propagates positions with SGP4."""

    name: ClassVar[str] = "satellites"

    def __init__(self, state: RealtimeState) -> None:
        super().__init__(state)
        self._cache_path = Path(".cache/tle.json")
        self._satrec_cache: dict[str, Satrec] = {}

    async def update(self) -> None:
        # 1. Fetch TLEs (group + prominent overrides).
        tle_entries = await self._fetch_tles()
        if not tle_entries:
            raise RuntimeError("no TLE data fetched (CelesTrak unreachable?)")

        # 2. Build Satrec objects, compute current position.
        now = datetime.now(timezone.utc)
        jd, fr = jday(
            now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6
        )

        satellites: dict[str, Satellite] = {}
        first_err: str | None = None
        for entry in tle_entries:
            try:
                norad = entry["norad"]
                if not norad:
                    continue
                line1 = entry["line1"]
                line2 = entry["line2"]
                sat = Satrec.twoline2rv(line1, line2)
                self._satrec_cache[norad] = sat
                e, r, v = sat.sgp4(jd, fr)
                if e != 0:
                    if first_err is None:
                        first_err = f"sgp4 error code {e} on NORAD {norad}"
                    continue  # SGP4 decode error — skip
                # sgp4 returns position in km (x, y, z) and velocity in km/s.
                lat, lon, alt = _teme_to_geodetic(r, now)
                velocity_kms = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5

                satellites[norad] = Satellite(
                    id=norad,
                    name=entry["name"],
                    category=_classify(entry["name"]),  # type: ignore[arg-type]
                    line1=line1,
                    line2=line2,
                    epoch=_parse_epoch_from_tle(line1),
                    intl_designator=entry.get("intl_designator") or None,
                    position=SatellitePosition(
                        lat=lat,
                        lon=lon,
                        alt_km=float(alt),
                        velocity_kms=float(velocity_kms),
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                if first_err is None:
                    first_err = f"{type(exc).__name__}: {exc} on NORAD {entry.get('norad')}"
                logger.debug(
                    "sat.decode_failed",
                    extra={"err": str(exc), "norad": entry.get("norad")},
                )
                continue

        if not satellites and first_err:
            logger.warning("sat.first_error", extra={"err": first_err})

        # 3. Commit.
        self.state.satellites = satellites
        self.state.tle_cache = {
            sid: (s.line1, s.line2) for sid, s in satellites.items()
        }
        await self.state.mark_ok(self.name, len(satellites))

    async def _fetch_tles(self) -> list[dict[str, Any]]:
        """Fetch TLEs from CelesTrak, with file cache fallback."""
        cached = _read_cache(self._cache_path)
        if cached and not _is_cache_stale(cached):
            return cached["entries"]

        all_entries: list[dict[str, str]] = []

        # Prominent (always-fetched)
        for name, info in _PROMINENT.items():
            try:
                text = await self.safe_get_text(info["url"], timeout=15)
                entries = _parse_tle_text(text)
                for e in entries:
                    e["norad"] = e.get("norad") or info["norad"]
                all_entries.extend(entries)
            except Exception as exc:  # noqa: BLE001
                logger.warning("sat.prominent_failed", extra={"name": name, "err": str(exc)})

        # Group fetches — silently skip on 403 (CelesTrak rate limit) or 404
        for group, url in _CELESTRAK_GROUPS.items():
            try:
                text = await self.safe_get_text(url, timeout=20)
                entries = _parse_tle_text(text)
                limit = _GROUP_LIMITS.get(group, 30)
                all_entries.extend(entries[:limit])
            except Exception as exc:  # noqa: BLE001
                logger.warning("sat.group_failed", extra={"group": group, "err": str(exc)})

        if all_entries:
            _write_cache(self._cache_path, all_entries)
        elif cached:
            # Network was flaky; serve stale cache
            logger.info("sat.serving_stale_cache")
            return cached["entries"]

        return all_entries


# ---------- helpers ---------------------------------------------------------


def _is_cache_stale(cached: dict[str, Any], max_age_seconds: int = 6 * 3600) -> bool:
    fetched_at = cached.get("fetched_at")
    if not fetched_at:
        return True
    try:
        ts = datetime.fromisoformat(fetched_at)
    except ValueError:
        return True
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age > max_age_seconds


def _read_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _teme_to_geodetic(r_km: tuple[float, float, float], when_utc: datetime) -> tuple[float, float, float]:
    """Convert TEME position (x, y, z) in km to (lat, lon, alt_km).

    Simplified WGS84 conversion. Accuracy ~0.1°, fine for globe-scale
    visualisation.
    """
    import math

    x, y, z = r_km
    jd, fr = jday(
        when_utc.year,
        when_utc.month,
        when_utc.day,
        when_utc.hour,
        when_utc.minute,
        when_utc.second + when_utc.microsecond / 1e6,
    )
    # Greenwich sidereal time (degrees) — IAU 1982 / simplified
    t = (jd - 2451545.0 + fr) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0 + fr)
        + 0.000387933 * t * t
        - (t ** 3) / 38710000.0
    )
    gmst = math.fmod(gmst, 360.0)
    theta = math.radians(gmst)

    # Rotate TEME → ECEF
    x_ecef = x * math.cos(-theta) - y * math.sin(-theta)
    y_ecef = x * math.sin(-theta) + y * math.cos(-theta)
    z_ecef = z

    # ECEF → geodetic
    a = 6378.137
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = 1 - (b * b) / (a * a)

    lon = math.atan2(y_ecef, x_ecef)
    p = math.hypot(x_ecef, y_ecef)
    lat = math.atan2(z_ecef, p * (1 - e2))
    for _ in range(5):
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        alt = p / math.cos(lat) - n
        lat = math.atan2(z_ecef, p * (1 - e2 * n / (n + alt)))
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - n

    return math.degrees(lat), math.degrees(lon), float(alt)
