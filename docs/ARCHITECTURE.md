# Architecture

This document explains how Realtime Earth is structured and how data flows
from the public sources to the user's screen.

## Bird's eye

```
        +-----------------------------+
        |   Public data providers     |
        |  CelesTrak  Blitzortung     |
        |  NASA FIRMS  USGS  GVP      |
        |  NOAA SWPC  SDO             |
        +-------------+---------------+
                      |  HTTPS / JSON / CSV
                      v
        +-----------------------------+
        |  Source adapters            |
        |  (BaseSource subclasses)    |
        |  - schedule, fetch, parse,  |
        |    normalize, store         |
        +-------------+---------------+
                      |
                      v
        +-----------------------------+
        |  In-memory state            |
        |  (RealtimeState singleton)  |
        |  - satellites{}             |
        |  - lightning[]              |
        |  - earthquakes[]            |
        |  - wildfires[]              |
        |  - volcanoes[]              |
        |  - solar snapshot           |
        +------+----------+-----------+
               |          |
       REST   |          |  WebSocket push
               v          v
        +-----------------------------+
        |  FastAPI routers            |
        |  /api/*    /healthz    /ws  |
        +-------------+---------------+
                      |
                      v
        +-----------------------------+
        |  Vue 3 + Cesium frontend    |
        |  - 3D globe                 |
        |  - Layer toggles            |
        |  - Sidebar panels           |
        |  - Detail popovers          |
        +-----------------------------+
```

## Module breakdown

### Backend (`backend/app/`)

| Module | Purpose |
|--------|---------|
| `main.py` | FastAPI app factory, lifespan (start/stop scheduler), CORS, static SPA mount |
| `core/config.py` | Pydantic-Settings — env-driven config |
| `core/logger.py` | JSON-line logger, third-party log levels |
| `core/state.py` | In-memory state singleton + status tracking |
| `core/scheduler.py` | APScheduler with one job per source |
| `models/schemas.py` | Pydantic wire models |
| `sources/base.py` | `BaseSource` — fetch + error capture + client |
| `sources/*.py` | One file per data source |
| `routers/health.py` | `/healthz`, `/api/meta` |
| `routers/satellites.py` | `/api/satellites/*` |
| `routers/lightning.py` | `/api/lightning/*` |
| `routers/earth.py` | `/api/earth/{earthquakes,wildfires,volcanoes}` |
| `routers/solar.py` | `/api/solar/*` |
| `routers/websocket.py` | `/ws` — pushes topic-snapshot messages |

### Frontend (`frontend/src/`)

| Module | Purpose |
|--------|---------|
| `main.ts` | Vue + Pinia bootstrap |
| `App.vue` | Layout — top bar, sidebar, detail panel, status bar, globe |
| `types.ts` | TypeScript mirror of backend Pydantic models |
| `stores/earth.ts` | Pinia store — one source of truth for layers, data, selection |
| `composables/useEarthWebSocket.ts` | Auto-reconnecting WebSocket |
| `components/GlobeView.vue` | Cesium viewer, layer rendering, click handler |
| `components/TopBar.vue` | Branding + uptime + WS status |
| `components/Sidebar.vue` | Tabbed data panel switcher |
| `components/StatusBar.vue` | Bottom source-status strip |
| `components/DetailPanel.vue` | Right-side detail for the selected item |
| `components/panels/*` | One panel per data source + a Layers toggle panel |
| `components/details/*` | Detail view for a selected satellite / earthquake / volcano |

## Data flow

1. **Scheduler** starts when the FastAPI app starts (`lifespan` in `main.py`).
2. For every enabled source, a job runs on its configured interval:
   - The job instantiates a `BaseSource` subclass.
   - The source subclass fetches its data via the public API/CSV.
   - On success, it writes the parsed records to `RealtimeState` and calls
     `state.mark_ok(name, count)`.
   - On failure, it raises; the scheduler catches it and calls
     `state.mark_error(name, exc)`.
3. **WebSocket** is the primary push channel. The server holds a single
   in-memory snapshot and pushes topic-snapshot messages every ~5 seconds
   (configurable per topic).
4. **REST** is for one-shot queries (filtered lightning, computed historical
   satellite position, etc.) and for the initial bootstrap the frontend does
   on page load so the UI is never empty.

## Adding a new source (TL;DR)

1. Add a Pydantic model in `app/models/schemas.py`.
2. Subclass `BaseSource` in `app/sources/<name>.py` — implement `update()`.
3. Add a state field in `app/core/state.py` (a list/dict and a status entry).
4. Add settings for enable / poll interval in `app/core/config.py`.
5. Register the source in `app/core/scheduler.py::build_scheduler()`.
6. Add a REST router in `app/routers/<name>.py` (optional but recommended).
7. Add a TS interface in `frontend/src/types.ts`.
8. Add a Pinia field + ingest branch in `frontend/src/stores/earth.ts`.
9. Add a panel + (optionally) a detail view under
   `frontend/src/components/panels/` and `details/`.
10. Wire it up in `App.vue` / `Sidebar.vue` / `GlobeView.vue`.

See [DEVELOPMENT.md](DEVELOPMENT.md) for a full worked example.

## Failure modes

- **Upstream flaky** — each source catches network errors and the scheduler
  marks the source as `error`. The next interval retries. The frontend shows
  a red dot next to the source name in the status bar.
- **Upstream slow** — `httpx` timeout is 30s by default; the next interval
  catches up automatically.
- **Container restart** — In-memory state is lost; sources re-fetch on boot.
  The lightning ring buffer is most affected; everything else is bounded by
  the upstream feed size.

## Performance notes

- Lightning has a `deque(maxlen=5000)` ring buffer to bound memory.
- Wildfires and earthquakes are bounded by `max_*` config settings.
- Cesium rendering is bounded by:
  - Lightning: last 2,000 strikes
  - Wildfires: up to 4,000 with confidence != "low"
  - Earthquakes: filtered to `mag >= 2.5` and `depth >= 50` to skip noise
  - Satellites: all (with `point` rendering, ~200–500 entities is fine)

If you push past these limits, tweak the limits in `GlobeView.vue`.

## Security

- All public data sources, no auth required.
- No user data is collected, no login, no cookies.
- CORS is set to the configured `cors_origins` (default localhost:8080/5173).
- WebSocket accepts any client — if you expose this beyond your LAN, put it
  behind a reverse proxy with auth (e.g. oauth2-proxy).
