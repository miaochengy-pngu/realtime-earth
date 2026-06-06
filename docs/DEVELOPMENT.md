# Development guide

This guide walks through adding a new data source to Realtime Earth. We'll
add a fictional "🌡️ Sea-surface temperature anomalies" layer as the example.

## 1. Add a Pydantic model

Edit `backend/app/models/schemas.py`:

```python
class SeaTempAnomaly(WireModel):
    id: str
    lat: float
    lon: float
    temp_anomaly_c: float          # °C deviation from seasonal mean
    timestamp: datetime
    source: str                    # e.g. "NOAA OISST"
```

## 2. Subclass `BaseSource`

Create `backend/app/sources/sea_temp.py`:

```python
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import ClassVar
from app.core.state import RealtimeState
from app.models.schemas import SeaTempAnomaly
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

URL = "https://example.com/oisst-anomalies.json"


class SeaTempSource(BaseSource):
    name: ClassVar[str] = "sea_temp"

    async def update(self) -> None:
        data = await self.safe_get_json(URL, timeout=30)
        items = []
        for row in data:
            items.append(SeaTempAnomaly(
                id=f"{row['lat']}-{row['lon']}-{row['date']}",
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                temp_anomaly_c=float(row["anomaly"]),
                timestamp=datetime.fromisoformat(row["date"]),
                source="NOAA OISST",
            ))
        # If you want the data to flow to the frontend, add a list to RealtimeState
        # (see step 3) and assign it here:
        #   self.state.sea_temp = items
        await self.state.mark_ok(self.name, len(items))
```

Register the class in `backend/app/sources/__init__.py`:

```python
from app.sources.sea_temp import SeaTempSource
```

## 3. Add state + settings

Edit `backend/app/core/state.py`:

```python
from app.models.schemas import (
    ...,
    SeaTempAnomaly,
)

class RealtimeState:
    def __init__(self) -> None:
        ...
        self.sea_temp: list[SeaTempAnomaly] = []
        ...
        self.status["sea_temp"] = {"ok": False, "error": None, "items": 0}
```

Edit `backend/app/core/config.py`:

```python
enable_sea_temp: bool = True
sea_temp_poll_seconds: int = 1800
```

## 4. Register in the scheduler

Edit `backend/app/core/scheduler.py`:

```python
from app.sources.sea_temp import SeaTempSource

sources: list[tuple[str, int, type]] = [
    ...,
    ("sea_temp", settings.sea_temp_poll_seconds, SeaTempSource),
]

toggles = {
    ...,
    "sea_temp": settings.enable_sea_temp,
}
```

## 5. Add a REST router (optional)

Create `backend/app/routers/sea_temp.py`:

```python
from fastapi import APIRouter
from app.core.state import state
from app.models.schemas import SeaTempAnomaly

router = APIRouter(prefix="/api/sea-temp", tags=["sea-temp"])


@router.get("", response_model=list[SeaTempAnomaly])
async def list_anomalies():
    return state.sea_temp
```

Register in `backend/app/routers/__init__.py` and in `main.py`:

```python
from app.routers import sea_temp_router
...
app.include_router(sea_temp_router)
```

## 6. Add WebSocket topic (optional)

In `backend/app/routers/websocket.py`, add a branch that pushes your data
when the client subscribes to `"sea_temp"`.

## 7. TypeScript interface

Edit `frontend/src/types.ts`:

```typescript
export interface SeaTempAnomaly {
  id: string;
  lat: number;
  lon: number;
  temp_anomaly_c: number;
  timestamp: string;
  source: string;
}
```

## 8. Pinia store

Edit `frontend/src/stores/earth.ts`:

```typescript
const seaTemp = ref<SeaTempAnomaly[]>([]);
// ...
function ingest(msg: WSMessage) {
  // ...
  case "sea_temp":
    seaTemp.value = (msg.data as SeaTempAnomaly[]) ?? [];
    break;
}
```

Add a layer toggle:

```typescript
const layers = ref({
  ...,
  seaTemp: true,
});
```

## 9. Add a Cesium layer

In `frontend/src/components/GlobeView.vue`, add a `renderSeaTemp()` function
and a new `CustomDataSource`. Pattern: see `renderEarthquakes()`.

## 10. Add a panel

Create `frontend/src/components/panels/SeaTempPanel.vue` showing a list or
heatmap. Register the tab in `Sidebar.vue`.

## 11. Add detail (optional)

Create `frontend/src/components/details/SeaTempDetail.vue` and wire
`store.selectedSeaTempId` in `DetailPanel.vue` and `GlobeView.vue`.

## 12. Test

```bash
# Backend
cd backend
pip install -e .[dev]
pytest -k sea_temp
ruff check app/sources/sea_temp.py

# Frontend
cd ../frontend
npm run build
```

## 13. Document

- Add a row to [DATA_SOURCES.md](DATA_SOURCES.md).
- Mention it in [README.md](../README.md).

That's it. The whole thing is meant to be modular — every step above is
isolated to a single file (or two), and nothing else needs to change.
