# Railway Architecture — Prod-test V1

Architecture overview for prod-test V1. **Operational contract (PR5):** [`railway_deploy_contract.md`](railway_deploy_contract.md). **Variables:** [`railway_variables.md`](railway_variables.md). **Config wiring:** [`infra/railway/README.md`](../../infra/railway/README.md).

Decisions are documented in this file and [`railway_deploy_contract.md`](railway_deploy_contract.md). Environment template: [`.env.prod-test.example`](../../.env.prod-test.example).

## Architecture (Option A only)

One Railway Project. One public service. No separate frontend service. No Cloudflare in the critical path (PR2–PR9).

```txt
Railway Project (prod-test V1)
├── api-web          [PUBLIC HTTPS]   nginx + SPA + Daphne + Channels
├── celery-worker    [PRIVATE]       Celery worker (mandatory)
├── celery-beat      [PRIVATE]       Celery Beat scheduler (mandatory)
├── postgres         [PRIVATE]       Railway PostgreSQL
├── redis            [PRIVATE]       Railway Redis
└── private media    volume on api-web only (worker ephemeral — see deploy contract)
```

Local analogues:

* Dev: [`docker-compose.yml`](../../docker-compose.yml) (`api`, `celery`, `celery-beat`, `postgres`, `redis`, `private_media` volume).
* Prod-test static + gateway (local only): [`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml) — nginx serves SPA + API same-origin on port 8080 (validates PR3 routing before Railway).

## Public routing (same-origin)

All traffic hits `https://<railway-domain>`:

| Path | Handler | Status |
|---|---|---|
| `/api/*` | Django / DRF / Daphne | Implemented |
| `/ws/*` | Django Channels / Daphne (WSS) | Implemented |
| `/*` | Frontend static SPA | Integrated in `api-web` on Railway ([`infra/docker/railway/Dockerfile.api-web`](../../infra/docker/railway/Dockerfile.api-web)); validated locally in PR3 |

The frontend API client uses `baseUrl: getApiBaseUrl()` ([`apps/web/src/api/client.ts`](../../apps/web/src/api/client.ts)). An empty `VITE_API_BASE_URL` keeps relative same-origin paths, so prod-test does not need a `VITE_*` API URL.

Web static cache: hashed `/assets/` are immutable; `index.html` is revalidated (`Cache-Control: no-cache`). No service worker.

## Services

| Service | Visibility | Image / command | Role |
|---|---|---|---|
| `api-web` | Public (Railway Public Networking, HTTPS) | [`infra/docker/railway/Dockerfile.api-web`](../../infra/docker/railway/Dockerfile.api-web); [`start-api-web.sh`](../../infra/docker/railway/start-api-web.sh) → nginx on `$PORT` + Daphne on `127.0.0.1:8000` | HTTP API, WebSocket, SPA static (same-origin) |
| `celery-worker` | Private | [`infra/docker/api/Dockerfile`](../../infra/docker/api/Dockerfile); `celery -A config worker` (**mandatory**) | Observation → signal pipeline, upload purge, chat purge, action-plan materialization |
| `celery-beat` | Private | Same backend Dockerfile; `celery -A config beat` (**mandatory**) | Scheduled tasks (horizon materialization, chat purge, upload TTL, stuck observation recovery) |
| `postgres` | Private | Railway PostgreSQL plugin | Business source of truth |
| `redis` | Private | Railway Redis plugin | Channels, Celery broker/result, cache/throttle |

`celery-beat` needs persistent schedule state: Railway volume at `/var/lib/celerybeat` (local dev uses `celerybeat_data` in Compose). See [`railway_deploy_contract.md`](railway_deploy_contract.md).

## Dependencies

```txt
api-web        → postgres, redis, private media volume
celery-worker  → postgres, redis (ephemeral media path — no shared volume)
celery-beat    → postgres, redis, beat schedule volume
```

Startup order: `postgres` and `redis` healthy before app services. `api-web` does not depend on Celery for the health endpoint, but observation processing requires a running worker.

## Environment variables by service

All backend services (`api-web`, `celery-worker`, `celery-beat`) share the same env contract ([`apps/api/config/settings.py`](../../apps/api/config/settings.py)). Differences:

| Variable group | `api-web` | `celery-worker` | `celery-beat` |
|---|---|---|---|
| Django security (`DJANGO_*`, `CSRF_*`) | yes | yes | yes |
| Postgres (`POSTGRES_*`) | yes | yes | yes |
| Redis / Celery (`REDIS_URL`, `CELERY_*`, `HOUSTON_CACHE_REDIS_URL`) | yes | yes | yes |
| OpenAI / AI providers | yes | yes | yes (pipeline runs on worker; beat does not call OpenAI directly) |
| Auth salts / peppers | yes | yes | yes |
| `HOUSTON_PRIVATE_MEDIA_ROOT` | yes (persistent volume) | yes (ephemeral path) | no (beat does not touch media files) |
| `HOUSTON_REGISTRATION_INVITE_CODES` | yes | no | no |
| `PORT` (Railway) | yes (Railway injects) | no public port | no public port |

Full reference: [`railway_variables.md`](railway_variables.md). Template: [`.env.prod-test.example`](../../.env.prod-test.example).

## Variable classification

| Category | Variables | How to set |
|---|---|---|
| **Public frontend** | none with secrets | Same-origin: no `VITE_*` API URL; no API secret belongs in `VITE_*` |
| **Backend-only** | `HOUSTON_PRIVATE_MEDIA_ROOT`, `HOUSTON_LOG_LEVEL`, beat schedule tuning vars | Set on relevant backend services |
| **Secrets (manual)** | `DJANGO_SECRET_KEY`, `OPENAI_API_KEY`, `HOUSTON_AUTH_TOKEN_PEPPER`, `HOUSTON_AUTH_TOKEN_SALT`, `HOUSTON_CHAT_WS_TICKET_SALT`, `HOUSTON_REALTIME_WS_TICKET_SALT` | Generate strong random values before first deploy; store in Railway service variables |
| **Railway-generated** | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `REDIS_URL` (from plugins) | Copy from Railway Postgres/Redis plugin reference vars into Houston names |
| **Manual (operator)** | `DJANGO_ALLOWED_HOSTS`, `HOUSTON_CLIENT_ORIGINS`, `HOUSTON_REGISTRATION_INVITE_CODES` | Public Railway domain + `healthcheck.railway.app` in allowed hosts; HTTPS SPA origin |

### Derived / mapped Redis URLs

Railway typically provides one Redis URL. Map to Houston's logical DB split (same pattern as local [`docker-compose.yml`](../../docker-compose.yml)):

| Houston variable | Purpose | Typical mapping |
|---|---|---|
| `REDIS_URL` | Django Channels | `redis://…/0` |
| `CELERY_BROKER_URL` | Celery broker | `redis://…/1` |
| `CELERY_RESULT_BACKEND` | Celery results | `redis://…/2` |
| `HOUSTON_CACHE_REDIS_URL` | Throttle / cache (prod) | `redis://…/3` (explicit recommended) |

Redis must remain on the Railway private network. **Do not expose Redis publicly.**

## Redis strategy

* Railway Redis plugin, private network only.
* Used for: Django Channels (`REDIS_URL`), Celery broker (`CELERY_BROKER_URL`), Celery results (`CELERY_RESULT_BACKEND`), cache/throttle (`HOUSTON_CACHE_REDIS_URL`).
* Not the source of business truth. Loss causes transient disruption (queued tasks, WS fan-out, throttle counters) but PostgreSQL remains authoritative.
* Monitor Redis connectivity from `api-web` and `celery-worker`.

## PostgreSQL strategy

* Railway PostgreSQL plugin, private network only.
* `POSTGRES_SSLMODE=require` in prod-test ([`.env.prod-test.example`](../../.env.prod-test.example)).
* **Migrations:** `api-web` pre-deploy only (`preDeployCommand` in [`infra/railway/api-web/railway.toml`](../../infra/railway/api-web/railway.toml)).
* **Bootstrap data:** after first migrate, run `python manage.py import_business_unit_catalog` (same as local `make bootstrap-dev` catalog step).
* **Backup (minimum before public testers):**
  * enable Railway Postgres daily backups (or equivalent `pg_dump` cron)
  * document restore: create new Postgres instance → restore dump → update `POSTGRES_*` on all services → redeploy
  * verify restore on a non-production copy before inviting external testers

## Private media strategy

* Photos linked to observations are persisted in `HOUSTON_PRIVATE_MEDIA_ROOT` (default `/app/apps/api/private_media`).
* Raw audio is never persisted; transcription uses temporary files only.
* No public `/media` URL — [`PrivateMediaStorage`](../../apps/api/houston/uploads/private_storage.py) raises on `.url()`; access is API-authorized only.
* **Railway V1:** persistent volume on `api-web` at `HOUSTON_PRIVATE_MEDIA_ROOT=/app/apps/api/private_media`. Worker uses ephemeral path only — cross-service purge/delete is **not fully guaranteed** (Railway cannot share volumes across services). Details: [`railway_deploy_contract.md`](railway_deploy_contract.md#known-limitations-v1--private-media).
* **Backup:** private photos must be backed up separately from PostgreSQL (volume snapshot or export). See deploy contract.

## Static cache

* Hashed Vite assets under `/assets/` may be cached long-term (`immutable`).
* `index.html` is always revalidated (`Cache-Control: no-cache`).
* No service worker, no web app manifest, no shell offline.
* Network-only for `/api/*`, `/ws/*`, uploads, transcription, private media, operational data.

## Celery strategy

* `celery-worker` and `celery-beat` are **mandatory** in prod-test.
* Beat schedules (from [`settings.py`](../../apps/api/config/settings.py)): action-plan horizon materialization, chat purge, upload TTL cleanup, stuck observation recovery.
* **Worker down = blocking:** submitted observations stay queued; AI signal generation stops. Treat worker health as a prod-test gate.
* Beat down = scheduled purges and horizon materialization stop (lazy read-path materialization remains a partial safety net for action plans).

## Healthcheck

* **Endpoint:** `GET /api/v1/health/` on `api-web` (returns `{"status": "ok"}`).
* Configure Railway healthcheck on `api-web` via [`infra/railway/api-web/railway.toml`](../../infra/railway/api-web/railway.toml) (`healthcheckPath = "/api/v1/health/"`).
* Include `healthcheck.railway.app` in `DJANGO_ALLOWED_HOSTS`.
* Healthcheck validates the API process only; it does not prove Celery or Redis are healthy. Monitor worker logs separately.

## Django security

Prod-test must pass the production security gate before traffic:

```bash
make backend-deploy-check
```

Operational detail, secret generation, Railway-required variables, local HTTP exceptions, and API docs policy: [`railway_security.md`](railway_security.md).

## Logs

* Structured stdout via Django logging (`HOUSTON_LOG_LEVEL`, default `INFO`).
* View logs per Railway service: `api-web`, `celery-worker`, `celery-beat`.
* Never log secrets, tokens, raw observation text, or private media paths in shareable tickets.

## Restart and redeploy

* **Env change:** update Railway service variables → redeploy/recreate affected services (`api-web`, `celery-worker`, `celery-beat`). No bind-mount `.env` in prod-test.
* **Code change:** rebuild backend image → redeploy all backend services.
* **Postgres/Redis:** managed plugins; restart via Railway dashboard if needed. App services reconnect.
* **No bind-mount:** unlike local Docker dev, prod-test does not mount the repo into containers.

## Cloudflare

**Out of scope for V1 and PR2–PR9.**

Future PR10+ may add Cloudflare for DNS, edge cache, or WAF **after** Railway prod-test is validated. No Workers, D1, or Durable Objects in prod-test V1.

## Explicit prohibitions

| Forbidden | Notes |
|---|---|
| `DJANGO_DEBUG=1` | Use `DJANGO_DEBUG=0` |
| Secrets in `VITE_*` | All AI keys, peppers, salts are backend-only |
| Public Redis | Private network only |
| `HOUSTON_AI_*_PROVIDER=fake` | Use `openai` with valid `OPENAI_API_KEY` |
| Public `/media` | Authorized API endpoints only |
| Separate Railway frontend service | Option A: SPA on `api-web` |
| Cloudflare critical path (PR2–PR9) | Railway Public Networking for HTTPS |

## Related documents

* [`railway_deploy_contract.md`](railway_deploy_contract.md) — operational deploy playbook (PR5)
* [`railway_variables.md`](railway_variables.md) — variable mapping and per-service matrix
* [`infra/railway/README.md`](../../infra/railway/README.md) — Railway config file wiring
* [`smoke_checklist.md`](smoke_checklist.md) — unified smoke
* [`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml) — local same-origin validation
* [`railway_security.md`](railway_security.md) — production security gate and secrets
* [`.env.prod-test.example`](../../.env.prod-test.example) — environment template
