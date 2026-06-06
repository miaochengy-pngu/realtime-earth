"""NOAA Space Weather Prediction Center (SWPC) data source.

Aggregates several SWPC public JSON feeds for solar and geomagnetic state:
  * Kp index           — https://services.swpc.noaa.gov/json/planetary_k_index_1m.json
  * Solar wind (DSCOVR/ACE) — https://services.swpc.noaa.gov/products/summary/10cm-flux-30-day.json
  * Sunspot number     — https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json
  * GOES X-ray         — https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json
  * Aurora probability — https://services.swpc.noaa.gov/json/ovation_aurora_latest.json
  * SDO image          — https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_HMIB.jpg

All endpoints are public. No API key required.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import ClassVar

from app.core.state import RealtimeState
from app.models.schemas import SolarSnapshot
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


_KP_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
_SUNSPOT_URL = "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json"
_XRAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json"
_SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/summary/solar-wind.json"
_OVATION_URL = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
_SDO_HMIB_URL = "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_HMIB.jpg"
_SDO_HMIIC_URL = "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_HMIIC.jpg"


_KP_DESCRIPTIONS = {
    0: "Quiet",
    1: "Quiet",
    2: "Quiet",
    3: "Unsettled",
    4: "Active",
    5: "Minor storm (G1)",
    6: "Moderate storm (G2)",
    7: "Strong storm (G3)",
    8: "Severe storm (G4)",
    9: "Extreme storm (G5)",
}


class SolarSource(BaseSource):
    """NOAA SWPC + NASA SDO solar snapshot."""

    name: ClassVar[str] = "solar"

    async def update(self) -> None:
        snapshot = SolarSnapshot(timestamp=datetime.now(timezone.utc))

        # Kp index
        try:
            data = await self.safe_get_json(_KP_URL, timeout=15)
            if isinstance(data, list) and data:
                # most-recent first; take first row
                latest = data[0]
                kp = latest.get("kp_index")
                if kp is not None:
                    snapshot.kp_index = float(kp)
                    rounded = int(round(float(kp)))
                    snapshot.kp_text = _KP_DESCRIPTIONS.get(rounded, "Unknown")
        except Exception as exc:  # noqa: BLE001
            logger.debug("solar.kp_failed", extra={"err": str(exc)})

        # Sunspot number
        try:
            data = await self.safe_get_json(_SUNSPOT_URL, timeout=15)
            if isinstance(data, list) and data:
                # last entry is usually the latest observation
                latest = data[-1]
                ssn = latest.get("ssn") or latest.get("sunspot_number")
                if ssn is not None:
                    snapshot.sunspot_number = int(ssn)
        except Exception as exc:  # noqa: BLE001
            logger.debug("solar.ssn_failed", extra={"err": str(exc)})

        # Solar wind (ACE / DSCOVR real-time)
        try:
            data = await self.safe_get_json(_SOLAR_WIND_URL, timeout=15)
            if isinstance(data, dict):
                if "WindSpeed" in data:
                    snapshot.solar_wind_speed_kms = float(data["WindSpeed"])
                if "Density" in data:
                    snapshot.solar_wind_density_pcm3 = float(data["Density"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("solar.wind_failed", extra={"err": str(exc)})

        # GOES X-ray class
        try:
            data = await self.safe_get_json(_XRAY_URL, timeout=15)
            if isinstance(data, list) and data:
                latest = data[-1]
                flux = latest.get("flux") or latest.get("xrsa_flux")
                if flux and float(flux) > 0:
                    snapshot.xray_class = _flux_to_xray_class(float(flux))
        except Exception as exc:  # noqa: BLE001
            logger.debug("solar.xray_failed", extra={"err": str(exc)})

        # Aurora probability (OVATION model)
        try:
            data = await self.safe_get_json(_OVATION_URL, timeout=15)
            if isinstance(data, dict):
                aurora_data = data.get("data", data)
                if isinstance(aurora_data, list) and aurora_data:
                    # Average the top of the forecast
                    probs = [float(p) for p in aurora_data if isinstance(p, (int, float))]
                    if probs:
                        snapshot.aurora_probability_north = max(probs) / 100.0
                        snapshot.aurora_probability_south = (
                            max(probs[: len(probs) // 2]) / 100.0 if len(probs) > 1 else None
                        )
        except Exception as exc:  # noqa: BLE001
            logger.debug("solar.ovation_failed", extra={"err": str(exc)})

        # SDO image — just pass the URL; the frontend loads it directly.
        snapshot.sdo_image_url = _SDO_HMIB_URL
        snapshot.sdo_image_timestamp = datetime.now(timezone.utc)

        self.state.solar = snapshot
        await self.state.mark_ok(self.name, 1)


def _flux_to_xray_class(flux: float) -> str:
    """GOES X-ray flux (W/m²) → class (A/B/C/M/X) and magnitude."""
    if flux < 1e-8:
        return "A"
    if flux < 1e-6:
        return f"B{flux / 1e-8:.1f}"
    if flux < 1e-5:
        return f"C{flux / 1e-6:.1f}"
    if flux < 1e-4:
        return f"M{flux / 1e-5:.1f}"
    return f"X{flux / 1e-4:.1f}"
