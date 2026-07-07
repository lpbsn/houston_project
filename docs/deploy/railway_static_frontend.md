# Railway static frontend — PR3 local validation

PR3 validates the **production frontend build** and **same-origin routing** locally. Railway deployment of the static SPA inside `api-web` is **PR5** — not implemented here.

## Dev vs prod-test

| | Local dev | Local prod-test (PR3) | Railway (PR5+) |
|---|---|---|---|
| Frontend | Vite dev (`make web-dev`) or Docker `web` service (`target: development`) | nginx serves `apps/web/dist` | nginx/Caddy inside `api-web` |
| API | `localhost:8000` or Vite proxy | via gateway `localhost:8080` | same public origin |
| Same-origin | Vite proxies `/api` and `/ws` | gateway routes `/api`, `/ws` → api; `/*` → static | single `api-web` entry |
| Build | none (HMR) | `npm run build` in Docker image | image build in CI/Railway |

Dev workflows are unchanged:

- `make up-backend` + `make web-dev` (recommended)
- `make up` — Docker `web` service uses Dockerfile `target: development` (Vite on port 5173)

Prod-test does **not** use `npm run dev` or `vite preview`.

## Local architecture (PR3)

```txt
Browser → http://localhost:8080 (gateway, only public host port)
            ├── /api/*  → api:8000 (Daphne)
            ├── /ws/*   → api:8000 (WebSocket upgrade)
            └── /*      → web-static:80 (nginx + SPA fallback)
```

Files:

- [`infra/docker/web/Dockerfile`](../../infra/docker/web/Dockerfile) — multi-stage: `build`, `development`, `production` (final)
- [`infra/docker/web/nginx.conf`](../../infra/docker/web/nginx.conf) — static server + cache headers
- [`infra/docker/gateway/nginx.conf`](../../infra/docker/gateway/nginx.conf) — same-origin reverse proxy
- [`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml) — isolated project (`houston-prod-test`)

Railway V1 keeps **one public service** (`api-web`). PR3 does not create a second Railway frontend service.

## Build the production web image

From repo root:

```bash
docker build -f infra/docker/web/Dockerfile .
```

Without `--target`, Docker builds the final `production` stage (nginx + `dist/`).

Compose dev explicitly selects `target: development` in [`docker-compose.yml`](../../docker-compose.yml).

## Run local prod-test stack

Prerequisites:

- `.env` present (same guard as dev: local Postgres only)
- First boot: migrations on the prod-test database

```bash
make up-prod-test          # starts gateway + web-static + api + postgres + redis
make migrate-prod-test     # first boot only (or after schema changes)
```

Open **http://localhost:8080** (not 5173 or 8000 directly).

Stop:

```bash
make down-prod-test
```

The prod-test stack uses project name `houston-prod-test` so volumes/networks do not collide with `docker compose` dev.

## Cache headers (web-static nginx)

| Path | Cache-Control |
|---|---|
| `/assets/*` | `public, max-age=31536000, immutable` |
| `/index.html` | `no-cache` |
| `/sw.js` | `no-cache` |
| `/workbox-*.js` | `no-cache` |
| `/manifest.webmanifest` | `no-cache` |

PWA service worker (`vite-plugin-pwa`) denies navigation fallback for `/api` and `/ws` at the SW layer ([`apps/web/vite.config.ts`](../../apps/web/vite.config.ts)). The gateway ensures those paths never reach the SPA nginx.

## Smoke tests

With the stack running on port 8080:

### Deep-link SPA reload

Each URL must return the SPA shell (`index.html` / React mount), not nginx 404:

```bash
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/signals
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/execution
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/chat/test
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/action-plans/executions/test
```

Expected: `200` with HTML containing `<div id="root">`.

### API must never return HTML

```bash
curl -sS http://localhost:8080/api/v1/health/
# → {"status":"ok"}

curl -sS http://localhost:8080/api/foo
# → Django 404 response, NOT index.html (no "<div id=\"root\">")
```

### Cache headers

```bash
curl -sSI http://localhost:8080/index.html | grep -i cache-control
curl -sSI http://localhost:8080/sw.js | grep -i cache-control
curl -sSI http://localhost:8080/manifest.webmanifest | grep -i cache-control
# Pick a hashed asset from dist:
curl -sSI http://localhost:8080/assets/<file>.js | grep -i cache-control
```

### Service worker and manifest

```bash
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/sw.js
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/manifest.webmanifest
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8080/spore-icon-192.png
```

Expected: `200` for all.

### WebSocket routing (proxy only)

The gateway forwards `/ws/` to Daphne with upgrade headers. A full authenticated WS session is out of PR3 scope; verify routing does not return SPA HTML:

```bash
curl -sS http://localhost:8080/ws/v1/establishments/00000000-0000-0000-0000-000000000000/realtime/
# → Django/Channels response (403/404/426), NOT index.html
```

## Gates (PR3)

```bash
cd apps/web && npm run build
cd apps/web && npm run typecheck
cd apps/web && npm test
docker build -f infra/docker/web/Dockerfile .
```

## What PR5 added

Railway deploy contract: [`railway_deploy_contract.md`](railway_deploy_contract.md). Same-origin routing is implemented in [`infra/docker/railway/Dockerfile.api-web`](../../infra/docker/railway/Dockerfile.api-web) + [`infra/docker/railway/nginx.conf`](../../infra/docker/railway/nginx.conf).

## Related

* [`railway_architecture.md`](railway_architecture.md) — Railway contract
* [`prod_test_decisions.md`](prod_test_decisions.md) — frozen decisions
