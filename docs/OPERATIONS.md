# Operations

This document covers running Realtime Earth in production-like environments.

## Production checklist

- [ ] Set a `REALTIME_EARTH_LOG_LEVEL=INFO` (or `WARNING` for less noise)
- [ ] Lock `REALTIME_EARTH_CORS_ORIGINS` to your actual frontend origin
- [ ] Set a free `REALTIME_EARTH_FIRMS_MAP_KEY` if you want higher FIRMS rate limits
- [ ] Mount a persistent volume on `backend/.cache` (so TLE cache survives restarts)
- [ ] Put the frontend behind TLS (Nginx + certbot, Caddy, or a managed LB)
- [ ] Add a `/healthz` monitor (UptimeRobot, Healthchecks.io, etc.)
- [ ] Configure log shipping (the backend emits JSON logs — easy to ship to Loki, Datadog, etc.)

## Recommended: Caddy

For a quick TLS-terminated deployment, [Caddy](https://caddyserver.com) is
the simplest option. Example `Caddyfile`:

```
realtime.example.com {
    reverse_proxy localhost:8080
}
```

That's it. Caddy will issue a Let's Encrypt cert automatically.

## Recommended: Nginx

If you prefer Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name realtime.example.com;

    ssl_certificate     /etc/letsencrypt/live/realtime.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/realtime.example.com/privkey.pem;

    # Forward to docker-compose on :8080
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 1h;
    }
}
```

## Resource sizing

Realtime Earth is lightweight. On a single Hetzner/OVH $5 VPS you can
comfortably run the full stack.

| Service | RAM (steady) | CPU (steady) | RAM (burst) |
|---------|--------------|--------------|-------------|
| Backend | ~120 MB | <5% | ~250 MB (during cold start) |
| Frontend | ~30 MB (Nginx) | <1% | ~50 MB |
| Total | **~150 MB** | **<6%** | ~300 MB |

Disk usage is dominated by:
- `backend/.cache/tle.json` (TLE cache, ~2 MB)
- npm/node_modules during build (only at build time, not at runtime)
- Docker layers (~1.5 GB)

## Rate-limiting etiquette

All upstream providers are free public services. The defaults are tuned to
be polite. If you fork and run an instance:

- **CelesTrak**: once per 30 min is plenty — TLEs only change every few hours
- **Blitzortung**: 10s polling is the upper bound; some operators prefer 30s
- **NASA FIRMS**: 30 min is the upstream cadence; more frequent is wasteful
- **USGS**: 1 min matches the upstream refresh
- **NOAA SWPC**: 1 min is the upstream refresh
- **Smithsonian GVP**: weekly is the upstream cadence

If you need higher rates, ask the upstream provider first.

## Logs

Backend logs are JSON (one object per line). Pipe to `jq` for human reading:

```bash
docker compose logs -f backend | jq -r '"\(.ts) [\(.level)] \(.msg) \(.source // "")"'
```

Fields:
- `ts` — ISO 8601 UTC timestamp
- `level` — `INFO` / `WARNING` / `ERROR`
- `logger` — Python logger name
- `msg` — message
- `source` — source name (on source events)
- `err` — error message (on failures)
- `items` — count (on success)

## Health check

`GET /healthz` returns:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 1234.5,
  "sources": {
    "satellites": { "ok": true, "items": 412, "last_updated": "2024-..." },
    ...
  },
  "counts": { "satellites": 412, "lightning": 1823, ... }
}
```

`status` is `ok` if **every** enabled source has succeeded at least once.
For Kubernetes-style readiness you may want a softer check — query the
`/api/meta` endpoint instead and treat any 200 as healthy.

## Upgrading

```bash
git pull
docker compose pull   # if you pull base images
docker compose up -d --build
```

The in-memory state is lost on restart; everything re-fetches within the
configured poll interval (lightning within 10s, satellites within 30 min).

## Backup / restore

There is no persistent data — Realtime Earth is a real-time read-only
view. The only thing to back up is your `.env` and any custom config.

If you need history, run a small sidecar that subscribes to `/ws` and
writes to a TSDB (Prometheus, InfluxDB, Timescale). See
[DEVELOPMENT.md](DEVELOPMENT.md) for the WS topic list.

## License & attribution notes for production

If you expose Realtime Earth to the public, please keep attribution
visible (we already do this in the lightning and solar panels). The data
providers we depend on:

| Source | Attribution requirement |
|--------|-------------------------|
| CelesTrak | None (public domain) |
| Blitzortung | Required (we render it) |
| NASA FIRMS | None (public domain) |
| USGS | None (public domain) |
| Smithsonian GVP | Required (we render it) |
| NOAA SWPC | None (public domain) |
| NASA SDO | None (public domain) |
