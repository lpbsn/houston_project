# Railway Architecture — Prod-test V1

Contract document for prod-test V1. **PR2 is docs-only** — no effective Railway or Cloudflare configuration is committed here.

Decisions are frozen in [`prod_test_decisions.md`](prod_test_decisions.md). Environment template: [`.env.prod-test.example`](../../.env.prod-test.example).

## Architecture (Option A only)

One Railway Project. One public service. No separate frontend service. No Cloudflare in the critical path (PR2–PR9).

```txt
Railway Project (prod-test V1)
├── api-web          [PUBLIC HTTPS]   Django + Daphne + Channels + future SPA static
├── celery-worker    [PRIVATE]       Celery worker (same backend image)
├── celery-beat      [PRIVATE]       Celery Beat scheduler (same backend image)
├── postgres         [PRIVATE]       Railway PostgreSQL
├── redis            [PRIVATE]       Railway Redis
└── (shared storage) private media   same logical path on api-web + celery-worker (mount TBD PR5)
```

Local analogues:

* Dev: [`docker-compose.yml`](../../docker-compose.yml) (`api`, `celery`, `celery-beat`, `postgres`, `redis`, `private_media` volume).
* Prod-test static + gateway (PR3, local only): [`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml) — see [`railway_static_frontend.md`](railway_static_frontend.md).

## Public routing (same-origin)

All traffic hits `https://<railway-domain>`:

| Path | Handler | Status |
|---|---|---|
| `/api/*` | Django / DRF / Daphne | Implemented |
| `/ws/*` | Django Channels / Daphne (WSS) | Implemented |
| `/*` | Frontend static SPA | **PR3** validates static + gateway locally; **PR5** integrates into `api-web` on Railway |

The frontend API client uses `baseUrl: ''` ([`apps/web/src/api/client.ts`](../../apps/web/src/api/client.ts)), so prod-test does not need a `VITE_*` API URL.

PWA workbox config is shell-only: `runtimeCaching: []`, `navigateFallbackDenylist: [/^\/api/, /^\/ws/]` ([`apps/web/vite.config.ts`](../../apps/web/vite.config.ts)).

## Services

| Service | Visibility | Image / command | Role |
|---|---|---|---|
| `api-web` | Public (Railway Public Networking, HTTPS) | Backend image; [`infra/docker/api/entrypoint.sh`](../../infra/docker/api/entrypoint.sh) → `daphne -b 0.0.0.0 -p 8000 config.asgi:application` | HTTP API, WebSocket; SPA static added in **PR5** (pattern validated locally in PR3) |
| `celery-worker` | Private | Same backend image; `celery -A config worker` | Observation → signal pipeline, upload purge, chat purge, action-plan materialization |
| `celery-beat` | Private | Same backend image; `celery -A config beat` | Scheduled tasks (horizon materialization, chat purge, upload TTL, stuck observation recovery) |
| `postgres` | Private | Railway PostgreSQL plugin | Business source of truth |
| `redis` | Private | Railway Redis plugin | Channels, Celery broker/result, cache/throttle |

`celery-beat` needs persistent schedule state (local dev uses a `celerybeat_data` volume in Compose). The Railway persistence approach will be defined in the deploy PR.

## Dependencies

```txt
api-web        → postgres, redis, shared private media storage
celery-worker  → postgres, redis, shared private media storage
celery-beat    → postgres, redis
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
| `HOUSTON_PRIVATE_MEDIA_ROOT` | yes | yes | no (beat does not touch media files) |
| `HOUSTON_REGISTRATION_INVITE_CODES` | yes | no | no |
| `PORT` (Railway) | yes (Railway injects) | no public port | no public port |

Full template: [`.env.prod-test.example`](../../.env.prod-test.example).

## Variable classification

| Category | Variables | How to set |
|---|---|---|
| **Public frontend** | none with secrets | Same-origin: no `VITE_*` API URL; no API secret belongs in `VITE_*` |
| **Backend-only** | `HOUSTON_PRIVATE_MEDIA_ROOT`, `HOUSTON_LOG_LEVEL`, beat schedule tuning vars | Set on relevant backend services |
| **Secrets (manual)** | `DJANGO_SECRET_KEY`, `OPENAI_API_KEY`, `HOUSTON_AUTH_TOKEN_PEPPER`, `HOUSTON_AUTH_TOKEN_SALT`, `HOUSTON_CHAT_WS_TICKET_SALT`, `HOUSTON_REALTIME_WS_TICKET_SALT` | Generate strong random values before first deploy; store in Railway service variables |
| **Railway-generated** | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `REDIS_URL` (from plugins) | Copy from Railway Postgres/Redis plugin reference vars into Houston names |
| **Manual (operator)** | `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `HOUSTON_REGISTRATION_INVITE_CODES` | Set from public Railway domain; invite codes per onboarding policy |

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
* **Migrations:** run `python manage.py migrate` as a pre-deploy step or documented one-shot command before traffic.
* **Bootstrap data:** after first migrate, run `python manage.py import_business_unit_catalog` (same as local `make bootstrap-dev` catalog step).
* **Backup (minimum before public testers):**
  * enable Railway Postgres daily backups (or equivalent `pg_dump` cron)
  * document restore: create new Postgres instance → restore dump → update `POSTGRES_*` on all services → redeploy
  * verify restore on a non-production copy before inviting external testers

## Private media strategy

* Photos linked to observations are persisted in `HOUSTON_PRIVATE_MEDIA_ROOT` (default `/app/apps/api/private_media`).
* Raw audio is never persisted; transcription uses temporary files only.
* No public `/media` URL — [`PrivateMediaStorage`](../../apps/api/houston/uploads/private_storage.py) raises on `.url()`; access is API-authorized only.
* **Shared storage requirement:** `api-web` and `celery-worker` must read/write/purge the same private storage at the same logical path. The exact Railway volume mount or alternative is validated in **PR5**.
* **Backup:** private photos must be backed up separately from PostgreSQL. Document a periodic export or volume snapshot procedure in the deploy PR.

## PWA strategy

* Shell and static build assets may be cached by the service worker.
* Network-only (never cached by SW): `/api/*`, `/ws/*`, uploads, transcription, private media, operational data.
* No offline business workflow. No offline queue. No background sync.
* Aligns with current [`vite.config.ts`](../../apps/web/vite.config.ts) (`runtimeCaching: []`).

## Celery strategy

* `celery-worker` and `celery-beat` are **mandatory** in prod-test.
* Beat schedules (from [`settings.py`](../../apps/api/config/settings.py)): action-plan horizon materialization, chat purge, upload TTL cleanup, stuck observation recovery.
* **Worker down = blocking:** submitted observations stay queued; AI signal generation stops. Treat worker health as a prod-test gate.
* Beat down = scheduled purges and horizon materialization stop (lazy read-path materialization remains a partial safety net for action plans).

## Healthcheck

* **Endpoint:** `GET /api/v1/health/` on `api-web` (returns `{"status": "ok"}`).
* Configure Railway healthcheck on `api-web` against this path over HTTPS.
* Healthcheck validates the API process only; it does not prove Celery or Redis are healthy. Monitor worker logs separately.

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

* [`prod_test_decisions.md`](prod_test_decisions.md) — decision log
* [`railway_static_frontend.md`](railway_static_frontend.md) — PR3 local static + gateway validation
* [`.env.prod-test.example`](../../.env.prod-test.example) — environment template
