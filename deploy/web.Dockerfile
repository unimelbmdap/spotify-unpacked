# syntax=docker/dockerfile:1.7
#
# Web tier: builds the Vue SPA and serves it with Caddy, which also reverse-
# proxies /api and /admin to the backend. Build context is the repo root.

# ---------- Build the SPA ----------
# Debian (glibc) rather than alpine to avoid musl issues with the native
# Tailwind v4 / lightningcss binaries. This whole stage is discarded.
FROM node:22-slim AS build

WORKDIR /app

# Install deps first for layer caching.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_API_BASE_URL is inlined into the bundle at build time. Empty string =
# same-origin: the browser calls /api and /admin on the host Caddy serves.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build-only

# ---------- Serve with Caddy ----------
FROM caddy:2-alpine AS runtime
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
