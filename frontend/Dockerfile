# Multi-stage build for the Realtime Earth frontend.
# Stage 1 — build the SPA with Vite
FROM node:20-alpine AS builder

WORKDIR /app

# Cache npm install
COPY package.json ./
RUN npm install --no-audit --no-fund

# Build with the right API/WS base paths so they go through the Nginx proxy
ARG VITE_API_BASE=/api
ARG VITE_WS_BASE=/ws
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_WS_BASE=${VITE_WS_BASE}

COPY . .
RUN npm run build

# Stage 2 — serve the SPA through Nginx and proxy /api + /ws to FastAPI
FROM nginx:1.27-alpine

# Nginx config (proxy /api and /ws to backend service)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Built SPA
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
