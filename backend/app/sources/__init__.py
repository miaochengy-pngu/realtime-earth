"""Data source adapters."""

from app.sources.base import BaseSource
from app.sources.earthquakes import EarthquakesSource
from app.sources.lightning import LightningSource
from app.sources.satellites import SatellitesSource
from app.sources.solar import SolarSource
from app.sources.volcanoes import VolcanoesSource
from app.sources.wildfires import WildfiresSource

__all__ = [
    "BaseSource",
    "EarthquakesSource",
    "LightningSource",
    "SatellitesSource",
    "SolarSource",
    "VolcanoesSource",
    "WildfiresSource",
]
