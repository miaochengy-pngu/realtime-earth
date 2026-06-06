# Data sources

Realtime Earth aggregates the following public, openly licensed data streams.
For each, we document the URL, the license, the cadence, and any caveats.

## 1. CelesTrak — Satellite TLE elements

| Field | Value |
|-------|-------|
| URL | <https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=json> |
| Specific satellites | <https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=json> |
| Cadence | We refresh every 30 min; TLEs go stale over hours-to-days |
| Format | JSON list of `{OBJECT_NAME, NORAD_CAT_ID, TLE_LINE_1, TLE_LINE_2, EPOCH, INTLDES, ...}` |
| License | Public Domain |
| Caveats | CelesTrak can rate-limit; we cap each group (Starlink 200, others 30) |

We use SGP4 (via the `sgp4` Python package) to propagate each TLE to the
current time and convert TEME → WGS84 lat/lon/alt.  Accuracy is plenty for
visualisation (≈0.1°).

## 2. Blitzortung — Community lightning network

| Field | Value |
|-------|-------|
| URL | <https://data.blitzortung.org/Data/Protected/lightning{,-na,-sa,-oc,-as,-af}.json> |
| Cadence | We poll every 10s per region |
| Format | JSON list of `[timestamp, lat, lon, alt_m, polarity, ?, ?]` |
| License | Free for non-commercial use with attribution |
| Caveats | Blitzortung is volunteer-run; **attribution required** if you deploy publicly |

We retain the last hour of strikes in a 5,000-element ring buffer.

## 3. NASA FIRMS — Active fire / thermal anomalies

| Field | Value |
|-------|-------|
| VIIRS 24h URL | <https://firms.modaps.eosdis.nasa.gov/data/active_fire/viirs/c2/csv/VL_C2_24h_GLOBAL.csv> |
| MODIS 24h URL | <https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis/c6/csv/MODIS_C6_24h_GLOBAL.csv> |
| Cadence | We poll every 30 min; NASA updates roughly every 3-6h |
| Format | CSV |
| License | Public Domain |
| Caveats | A free MAP_KEY (env: `REALTIME_EARTH_FIRMS_MAP_KEY`) raises the rate limit; not required |

`confidence` field is normalised to `low` / `nominal` / `high`.

## 4. USGS Earthquake Hazards Program

| Field | Value |
|-------|-------|
| Hourly feed | <https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson> |
| Daily feed | <https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson> |
| Cadence | We poll both every minute; the hour feed has the freshest data |
| Format | GeoJSON FeatureCollection |
| License | Public Domain |

We deduplicate by `id` and store the union.

## 5. Smithsonian GVP — Volcanoes

| Field | Value |
|-------|-------|
| Weekly bulletin | <https://volcano.si.edu/database/webservices.cfm?type=Weekly> |
| Cadence | We poll weekly |
| Format | HTML (we do lightweight text scraping) |
| License | Free for non-commercial use with attribution |
| Caveats | The weekly feed is HTML and flaky. We ship a hand-curated baseline of ~50 currently active / notable volcanoes so the layer is never empty. |

The baseline includes coordinates and current activity level (curated).

## 6. NOAA SWPC — Space weather

| Field | Value |
|-------|-------|
| Kp index | <https://services.swpc.noaa.gov/json/planetary_k_index_1m.json> |
| Sunspot number | <https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json> |
| GOES X-ray | <https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json> |
| Solar wind | <https://services.swpc.noaa.gov/products/summary/solar-wind.json> |
| Aurora probability | <https://services.swpc.noaa.gov/json/ovation_aurora_latest.json> |
| Cadence | We poll every minute |
| License | Public Domain |

## 7. NASA SDO — Solar imagery

| Field | Value |
|-------|-------|
| Latest HMI continuum | <https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_HMIB.jpg> |
| Cadence | We don't poll; the image URL is cached for the frontend to refresh on each push |
| License | Public Domain |

The SDO image is **not** proxied by our backend — the frontend loads it
directly from NASA. The `<img>` tag appends a cache-buster timestamp.

## Adding a new source

See [DEVELOPMENT.md](DEVELOPMENT.md) for a step-by-step walkthrough.
