"""REST + WebSocket routers."""

from app.routers.health import router as health_router
from app.routers.websocket import router as ws_router
from app.routers.satellites import router as satellites_router
from app.routers.lightning import router as lightning_router
from app.routers.earth import router as earth_router
from app.routers.solar import router as solar_router

__all__ = [
    "health_router",
    "ws_router",
    "satellites_router",
    "lightning_router",
    "earth_router",
    "solar_router",
]
