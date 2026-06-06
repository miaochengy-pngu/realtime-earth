"""Pluggable data source interface.

Every Realtime Earth data source is a subclass of `BaseSource`. To add a new
source:

    1. Subclass `BaseSource`
    2. Set `name` to a stable identifier (used in URLs, WS topics, status)
    3. Implement `async def update(self) -> None`
    4. Register it in `app.core.scheduler.build_scheduler`
    5. Add a Pydantic model in `app.models.schemas` for your data
    6. Add a REST endpoint in `app.routers.<your_source>` and a WS topic

See `docs/DEVELOPMENT.md` for a worked example.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

import httpx

from app.core.state import RealtimeState

logger = logging.getLogger(__name__)


class BaseSource(abc.ABC):
    """Abstract base for all data sources.

    Concrete subclasses must set `name` and implement `update()`.
    The base class provides:
      * a configured `httpx.AsyncClient` with sane timeouts
      * access to the shared `RealtimeState`
      * a uniform `safe_get` helper that catches network errors
    """

    #: Stable identifier used in API paths, status keys, WS topics.
    name: str = ""

    def __init__(self, state: RealtimeState, *, timeout: float = 30.0) -> None:
        if not self.name:
            raise ValueError(f"{type(self).__name__} must set .name")
        self.state = state
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            from app.core.config import get_settings

            settings = get_settings()
            self._client = httpx.AsyncClient(
                timeout=settings.http_timeout_seconds,
                headers={"User-Agent": settings.http_user_agent},
                follow_redirects=True,
                http2=False,  # many public APIs don't support h2
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @abc.abstractmethod
    async def update(self) -> None:
        """Fetch fresh data and update the shared state.

        Implementations should be idempotent and tolerant of transient errors.
        On success, call `self.state.mark_ok(self.name, count)`.
        On failure, raise — the scheduler will catch it and call
        `self.state.mark_error`.
        """

    async def safe_get(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET with a single retry on network errors. Raises on hard failure."""
        client = await self._get_client()
        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                return await client.get(url, **kwargs)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "source.http_retry",
                    extra={"source": self.name, "url": url, "attempt": attempt, "err": str(exc)},
                )
        assert last_exc is not None
        raise last_exc

    async def safe_get_json(self, url: str, **kwargs: Any) -> Any:
        """GET and parse JSON."""
        resp = await self.safe_get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def safe_get_text(self, url: str, **kwargs: Any) -> str:
        """GET and return text."""
        resp = await self.safe_get(url, **kwargs)
        resp.raise_for_status()
        return resp.text

    async def safe_get_bytes(self, url: str, **kwargs: Any) -> bytes:
        """GET and return raw bytes (e.g. for image fetches)."""
        resp = await self.safe_get(url, **kwargs)
        resp.raise_for_status()
        return resp.content
