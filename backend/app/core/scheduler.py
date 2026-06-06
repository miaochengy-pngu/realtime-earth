"""APScheduler setup — one periodic job per data source."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.state import state
from app.sources.earthquakes import EarthquakesSource
from app.sources.lightning import LightningSource
from app.sources.satellites import SatellitesSource
from app.sources.solar import SolarSource
from app.sources.volcanoes import VolcanoesSource
from app.sources.wildfires import WildfiresSource

logger = logging.getLogger(__name__)


async def _run(name: str, coro_factory: Callable[[], Awaitable[None]]) -> None:
    """Run a source update, capturing errors into the shared state."""
    try:
        await coro_factory()
        items = state.status[name].get("items", 0)
        await state.mark_ok(name, items)
        logger.info("source.updated", extra={"source": name, "items": items})
    except Exception as exc:  # noqa: BLE001
        await state.mark_error(name, exc)
        logger.exception("source.failed", extra={"source": name})


def build_scheduler() -> AsyncIOScheduler:
    """Build the AsyncIOScheduler with jobs for every enabled source."""
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")

    sources: list[tuple[str, int, type]] = [
        ("satellites", settings.satellite_poll_seconds, SatellitesSource),
        ("lightning", settings.lightning_poll_seconds, LightningSource),
        ("earthquakes", settings.earthquake_poll_seconds, EarthquakesSource),
        ("wildfires", settings.wildfire_poll_seconds, WildfiresSource),
        ("volcanoes", settings.volcano_poll_seconds, VolcanoesSource),
        ("solar", settings.solar_poll_seconds, SolarSource),
    ]

    toggles = {
        "satellites": settings.enable_satellites,
        "lightning": settings.enable_lightning,
        "earthquakes": settings.enable_earthquakes,
        "wildfires": settings.enable_wildfires,
        "volcanoes": settings.enable_volcanoes,
        "solar": settings.enable_solar,
    }

    for name, seconds, cls in sources:
        if not toggles.get(name, False):
            logger.info("source.disabled", extra={"source": name})
            continue

        # Instantiate the source class with the shared state.
        source_obj = cls(state=state)  # type: ignore[arg-type]

        async def _job(_name: str = name, _src=source_obj) -> None:  # noqa: ANN001
            logger.info("source.job_starting", extra={"source": _name})
            try:
                await _run(_name, _src.update)
            except Exception as exc:
                logger.exception("source.job_failed", extra={"source": _name, "err": str(exc)})

        scheduler.add_job(
            _job,
            trigger=IntervalTrigger(seconds=seconds, jitter=min(30, seconds // 4)),
            id=name,
            name=f"poll:{name}",
            max_instances=1,
            coalesce=True,
            # Run immediately on startup so the UI is never empty.
            next_run_time=datetime.now(tz=timezone.utc),
        )

    return scheduler
