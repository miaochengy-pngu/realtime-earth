"""FastAPI application factory + ASGI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.core.scheduler import build_scheduler
from app.routers import (
    earth_router,
    health_router,
    lightning_router,
    satellites_router,
    solar_router,
    ws_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the data-source scheduler on app startup; stop it on shutdown."""
    configure_logging()
    settings = get_settings()
    Path(settings.cache_dir).mkdir(parents=True, exist_ok=True)

    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info(
        "app.started",
        extra={"version": __version__, "log_level": settings.log_level},
    )
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("app.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Realtime Earth",
        version=__version__,
        description="Real-time tracker for public, open data — satellites, lightning, earthquakes, fires, volcanoes, space weather.",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # CORS — dev-friendly; tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(satellites_router)
    app.include_router(lightning_router)
    app.include_router(earth_router)
    app.include_router(solar_router)
    app.include_router(ws_router)

    # Optional: serve the built frontend in production (Docker)
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
        logger.info("frontend.served", extra={"path": str(frontend_dist)})

    return app


app = create_app()
