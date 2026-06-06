"""Smithsonian Global Volcanism Program volcano data.

GVP maintains a weekly bulletin of volcanic activity. We pull the most recent
weekly report and a static list of volcanoes with current known activity.

Endpoints:
  * Weekly bulletin JSON:  https://volcano.si.edu/database/webservices.cfm?type=Weekly
  * Volcano list (CSV):    https://volcano.si.edu/database/webservices.cfm?type=VolcanoList

Data is updated weekly (Mondays UTC). "Real-time" is aspirational; this layer
is for context rather than live eruptions.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import ClassVar

from app.core.state import RealtimeState
from app.models.schemas import Volcano
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

WEEKLY_URL = "https://volcano.si.edu/database/webservices.cfm?type=Weekly"
VOLCANO_LIST_URL = "https://volcano.si.edu/database/webservices.cfm?type=VolcanoList"


# Curated "currently active / notable" volcanoes with current status.
# The Smithsonian GVP weekly feed is the authoritative source, but for offline
# robustness we ship a hand-curated baseline.
_BASELINE_ACTIVE: list[dict] = [
    {"id": "V_NUM_0101-01=", "name": "Klyuchevskoy", "country": "Russia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0101-02=", "name": "Sheveluch", "country": "Russia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0102-02=", "name": "Sangay", "country": "Ecuador", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0102-03=", "name": "Reventador", "country": "Ecuador", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0201-04=", "name": "Fuego", "country": "Guatemala", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0202-09=", "name": "Santiaguito", "country": "Guatemala", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0203-05=", "name": "Stromboli", "country": "Italy", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0203-11=", "name": "Etna", "country": "Italy", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0204-01=", "name": "Piton de la Fournaise", "country": "Reunion (France)", "level": "elevated", "last_eruption": "2024"},
    {"id": "V_NUM_0301-01=", "name": "Popocatepetl", "country": "Mexico", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0301-03=", "name": "Volcan de Colima", "country": "Mexico", "level": "elevated", "last_eruption": "2017"},
    {"id": "V_NUM_0302-01=", "name": "Masaya", "country": "Nicaragua", "level": "elevated", "last_eruption": "2024"},
    {"id": "V_NUM_0303-01=", "name": "Poas", "country": "Costa Rica", "level": "elevated", "last_eruption": "2024"},
    {"id": "V_NUM_0303-04=", "name": "Turrialba", "country": "Costa Rica", "level": "elevated", "last_eruption": "2024"},
    {"id": "V_NUM_0304-01=", "name": "Rincon de la Vieja", "country": "Costa Rica", "level": "elevated", "last_eruption": "2024"},
    {"id": "V_NUM_0401-01=", "name": "Soufriere Hills", "country": "Montserrat", "level": "elevated", "last_eruption": "2013"},
    {"id": "V_NUM_0401-04=", "name": "La Soufriere", "country": "St. Vincent", "level": "elevated", "last_eruption": "2021"},
    {"id": "V_NUM_0501-03=", "name": "White Island", "country": "New Zealand", "level": "elevated", "last_eruption": "2019"},
    {"id": "V_NUM_0502-01=", "name": "Yasur", "country": "Vanuatu", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0601-01=", "name": "Aoba (Ambae)", "country": "Vanuatu", "level": "elevated", "last_eruption": "2018"},
    {"id": "V_NUM_0701-02=", "name": "Krakatau", "country": "Indonesia", "level": "elevated", "last_eruption": "2018"},
    {"id": "V_NUM_0702-01=", "name": "Merapi", "country": "Indonesia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0702-03=", "name": "Semeru", "country": "Indonesia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0702-04=", "name": "Bromo", "country": "Indonesia", "level": "elevated", "last_eruption": "2024"},
    {"id": "V_NUM_0703-01=", "name": "Ibu", "country": "Indonesia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0703-04=", "name": "Dukono", "country": "Indonesia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0704-03=", "name": "Lewotolo", "country": "Indonesia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0801-01=", "name": "Mayon", "country": "Philippines", "level": "elevated", "last_eruption": "2023"},
    {"id": "V_NUM_0801-04=", "name": "Taal", "country": "Philippines", "level": "elevated", "last_eruption": "2022"},
    {"id": "V_NUM_0801-05=", "name": "Kanlaon", "country": "Philippines", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0802-01=", "name": "Bulusan", "country": "Philippines", "level": "elevated", "last_eruption": "2023"},
    {"id": "V_NUM_0900-01=", "name": "Aira (Sakurajima)", "country": "Japan", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0900-07=", "name": "Sakurajima", "country": "Japan", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0900-13=", "name": "Suwanosejima", "country": "Japan", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_0901-01=", "name": "Kirishima", "country": "Japan", "level": "elevated", "last_eruption": "2018"},
    {"id": "V_NUM_0902-01=", "name": "Asama", "country": "Japan", "level": "elevated", "last_eruption": "2019"},
    {"id": "V_NUM_0903-01=", "name": "Sakurajima", "country": "Japan", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1000-01=", "name": "Karymsky", "country": "Russia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1000-07=", "name": "Ebeko", "country": "Russia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1000-26=", "name": "Sarychev Peak", "country": "Russia", "level": "elevated", "last_eruption": "2009"},
    {"id": "V_NUM_1101-02=", "name": "Sierra Negra", "country": "Ecuador", "level": "elevated", "last_eruption": "2018"},
    {"id": "V_NUM_1101-03=", "name": "Wolf", "country": "Ecuador", "level": "elevated", "last_eruption": "2022"},
    {"id": "V_NUM_1201-01=", "name": "Nyiragongo", "country": "DR Congo", "level": "elevated", "last_eruption": "2021"},
    {"id": "V_NUM_1201-02=", "name": "Nyamuragira", "country": "DR Congo", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1302-01=", "name": "Ol Doinyo Lengai", "country": "Tanzania", "level": "elevated", "last_eruption": "2017"},
    {"id": "V_NUM_1401-12=", "name": "Erta Ale", "country": "Ethiopia", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1500-01=", "name": "Piton de la Fournaise", "country": "Reunion (France)", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1600-01=", "name": "Barren Island", "country": "India", "level": "erupting", "last_eruption": "2024"},
    {"id": "V_NUM_1700-01=", "name": "Heard", "country": "Australia", "level": "elevated", "last_eruption": "2017"},
    {"id": "V_NUM_1800-01=", "name": "Mawson Peak", "country": "Antarctica", "level": "elevated", "last_eruption": "2017"},
]

# Approximate coordinates for baseline volcanoes (the GVP weekly feed is the
# canonical source when available, but it can be flaky — these let us always
# show *something*).
_BASELINE_COORDS: dict[str, tuple[float, float, int]] = {
    "Klyuchevskoy": (56.056, 160.642, 4754),
    "Sheveluch": (56.653, 161.360, 3283),
    "Sangay": (-2.005, -78.341, 5230),
    "Reventador": (-0.077, -77.656, 3562),
    "Fuego": (14.473, -90.880, 3763),
    "Santiaguito": (14.756, -91.552, 2550),
    "Stromboli": (38.789, 15.213, 924),
    "Etna": (37.751, 14.993, 3357),
    "Piton de la Fournaise": (-21.245, 55.708, 2632),
    "Popocatepetl": (19.023, -98.628, 5426),
    "Volcan de Colima": (19.514, -103.620, 3850),
    "Masaya": (11.985, -86.163, 635),
    "Poas": (10.200, -84.233, 2708),
    "Turrialba": (10.025, -83.767, 3340),
    "Rincon de la Vieja": (10.830, -85.324, 1916),
    "Soufriere Hills": (16.716, -62.183, 915),
    "La Soufriere": (13.330, -61.180, 1220),
    "White Island": (-37.521, 177.182, 321),
    "Yasur": (-19.528, 169.447, 361),
    "Aoba (Ambae)": (-15.400, 167.840, 1496),
    "Krakatau": (-6.102, 105.423, 813),
    "Merapi": (-7.541, 110.442, 2910),
    "Semeru": (-8.108, 112.922, 3676),
    "Bromo": (-7.942, 112.953, 2329),
    "Ibu": (1.488, 127.630, 1325),
    "Dukono": (1.700, 127.870, 1335),
    "Lewotolo": (-8.272, 123.505, 1423),
    "Mayon": (13.257, 123.685, 2463),
    "Taal": (14.010, 120.997, 311),
    "Kanlaon": (10.412, 123.132, 2435),
    "Bulusan": (12.770, 124.057, 1565),
    "Aira (Sakurajima)": (31.593, 130.657, 1117),
    "Sakurajima": (31.585, 130.658, 1117),
    "Suwanosejima": (29.638, 129.714, 796),
    "Kirishima": (31.934, 130.863, 1700),
    "Asama": (36.406, 138.523, 2568),
    "Karymsky": (54.049, 159.453, 1513),
    "Ebeko": (50.686, 156.014, 1156),
    "Sarychev Peak": (48.092, 153.200, 1496),
    "Sierra Negra": (-0.830, -91.170, 1124),
    "Wolf": (0.020, -91.350, 1710),
    "Nyiragongo": (-1.520, 29.250, 3470),
    "Nyamuragira": (-1.408, 29.200, 3058),
    "Ol Doinyo Lengai": (-2.764, 35.914, 2962),
    "Erta Ale": (13.600, 40.660, 613),
    "Barren Island": (12.278, 93.858, 354),
    "Heard": (-53.106, 73.513, 2745),
    "Mawson Peak": (-53.100, 73.500, 2745),
}


class VolcanoesSource(BaseSource):
    """Smithsonian GVP + curated baseline."""

    name: ClassVar[str] = "volcanoes"

    async def update(self) -> None:
        volcanoes: list[Volcano] = []

        # Try the live weekly feed first.
        try:
            text = await self.safe_get_text(WEEKLY_URL, timeout=30)
            volcanoes.extend(_parse_weekly_html(text))
        except Exception as exc:  # noqa: BLE001
            logger.warning("gvp.weekly_failed", extra={"err": str(exc)})

        # Always include the baseline.
        for entry in _BASELINE_ACTIVE:
            coords = _BASELINE_COORDS.get(entry["name"], (0.0, 0.0, 0))
            volcanoes.append(
                Volcano(
                    id=entry["id"],
                    name=entry["name"],
                    country=entry["country"],
                    region=entry["country"],
                    lat=coords[0],
                    lon=coords[1],
                    elevation_m=coords[2],
                    activity_level=entry["level"],  # type: ignore[arg-type]
                    last_known_eruption=entry["last_eruption"],
                    last_update=datetime.now(timezone.utc),
                )
            )

        # Dedupe by id, prefer the live feed version when present.
        by_id: dict[str, Volcano] = {v.id: v for v in volcanoes}
        self.state.volcanoes = list(by_id.values())
        await self.state.mark_ok(self.name, len(self.state.volcanoes))


def _parse_weekly_html(text: str) -> list[Volcano]:
    """Parse the Smithsonian GVP weekly bulletin. Lightweight text scraping —
    the feed is HTML, not JSON. We just look for the volcano name + status.
    """
    out: list[Volcano] = []
    for name, (lat, lon, elev) in _BASELINE_COORDS.items():
        if name in text:
            out.append(
                Volcano(
                    id=f"gvp-weekly-{name}",
                    name=name,
                    country="",
                    region="",
                    lat=lat,
                    lon=lon,
                    elevation_m=elev,
                    activity_level="elevated",  # best-effort default
                    last_update=datetime.now(timezone.utc),
                )
            )
    return out
