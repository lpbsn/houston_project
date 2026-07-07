# Railway Deploy Contract — Prod-test V1

Operational playbook for deploying Houston on Railway. Architecture context: [`railway_architecture.md`](railway_architecture.md). Variables: [`railway_variables.md`](railway_variables.md). Config wiring: [`infra/railway/README.md`](../../infra/railway/README.md).

**PR5 delivers the concrete contract.** `celery-worker` and `celery-beat` are **mandatory** in prod-test — not optional.

## Project topology

```txt
Railway Project (prod-test V1)
├── api-web          [PUBLIC HTTPS]   nginx + SPA + Daphne + Channels
├── celery-worker    [PRIVATE]       Celery worker (mandatory)
├── celery-beat      [PRIVATE]       Celery Beat scheduler (mandatory)
├── postgres         [PRIVATE]       Railway PostgreSQL plugin
└── redis            [PRIVATE]       Railway Redis plugin
```

Same-origin public routing on `https://<railway-domain>`:

| Path | Handler |
|---|---|
| `/api/*` | Django / DRF / Daphne |
| `/ws/*` | Django Channels / Daphne (WSS) |
| `/*` | Frontend static SPA |

## Prerequisites

* Railway account and GitHub access to the Houston repository
* OpenAI API key (prod-test uses real `openai` providers)
* Secrets generated per [`railway_security.md`](railway_security.md)
* Local gate passed before first deploy: `make backend-deploy-check`

## Config as code wiring

Railway does **not** auto-discover `infra/railway/*/railway.toml`. For each application service:

| Setting | Value |
|---|---|
| Root Directory | `/` (repository root) |
| Config File path | `/infra/railway/<service>/railway.toml` (absolute from repo root) |

See [`infra/railway/README.md`](../../infra/railway/README.md) for step-by-step setup.

---

## Service: `api-web`

| Field | Value |
|---|---|
| Source | GitHub repository (same repo as workers) |
| Root Directory | `/` |
| Config File | `/infra/railway/api-web/railway.toml` |
| Dockerfile | `infra/docker/railway/Dockerfile.api-web` (via `dockerfilePath` in toml) |
| Visibility | **Public** (Railway Public Networking + HTTPS) |
| Depends on | `postgres`, `redis` healthy; env vars configured |

### Build

Railway builds with `builder = "DOCKERFILE"` and `dockerfilePath = "infra/docker/railway/Dockerfile.api-web"` (relative to Root Directory `/`).

The image includes: Python API (uv), production SPA build (`apps/web/dist`), nginx edge config.

### Pre-deploy (migrations only)

Configured in [`infra/railway/api-web/railway.toml`](../../infra/railway/api-web/railway.toml):

```toml
preDeployCommand = "cd /app/apps/api && uv run python manage.py migrate"
```

* Runs in a **separate container** before the new deployment goes live.
* **Volumes are not mounted** during pre-deploy — migrations are DB-only (safe).
* **Workers and beat do not run migrations.**

If pre-deploy fails: fix the error, or run migrate manually (Railway shell / one-off) before accepting traffic.

### Post-migrate bootstrap (manual)

After first migrate (or schema change), run **once** manually:

```bash
cd /app/apps/api && uv run python manage.py import_business_unit_catalog
```

Use Railway service shell or `railway run` against `api-web`. Not automated in pre-deploy.

### Start command

```toml
startCommand = "/app/infra/docker/railway/start-api-web.sh"
```

The script ([`infra/docker/railway/start-api-web.sh`](../../infra/docker/railway/start-api-web.sh)):

* Sets `PORT="${PORT:-8080}"`
* Runs `check --deploy` when `DJANGO_DEBUG=0`
* Starts **Daphne** on `127.0.0.1:8000` (HTTP + WebSocket)
* Starts **nginx** on `0.0.0.0:$PORT` (Railway edge)
* Routes `/api/*` and `/ws/*` to Daphne; `/*` to SPA static
* Exits non-zero if Daphne or nginx fails

No `$PORT` logic in `railway.toml` — only in the start script.

### Healthcheck

| Setting | Value |
|---|---|
| Railway `healthcheckPath` | `/api/v1/health/` |
| Expected response | `200` + `{"status":"ok"}` |
| Proves | API process + nginx routing only |

Railway queries from hostname `healthcheck.railway.app` — include it in `DJANGO_ALLOWED_HOSTS` (see [`railway_variables.md`](railway_variables.md)).

### Volume (private media)

| Mount path | Variable |
|---|---|
| `/app/apps/api/private_media` | `HOUSTON_PRIVATE_MEDIA_ROOT=/app/apps/api/private_media` |

Add a Railway volume on `api-web` mounted at this path. Verify write access after deploy (upload smoke test).

Railway volumes mount as root; the start script `chown`s the media directory. If permission issues persist, set `RAILWAY_RUN_UID=0` on the service.

### Domain

1. Enable Railway Public Networking on `api-web`.
2. Generate or attach a domain (`*.railway.app` or Railway custom domain).
3. Set `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (see variables doc).

---

## Service: `celery-worker` (mandatory)

| Field | Value |
|---|---|
| Source | Same GitHub repository |
| Root Directory | `/` |
| Config File | `/infra/railway/celery-worker/railway.toml` |
| Dockerfile | `infra/docker/api/Dockerfile` |
| Visibility | Private (no public port) |
| Depends on | `postgres`, `redis` |

### Start command

```toml
startCommand = "cd /app/apps/api && uv run celery -A config worker -l info -n houston-worker@%h"
```

### Health / verification

No HTTP healthcheck. Verify in Railway logs:

* `celery@houston-worker` ready message
* Worker processes tasks when observations are submitted

**Prod-test is broken** if the worker is down: observation processing and AI signal generation stop.

### Volume

**No persistent volume.** Use ephemeral writable path for deploy checks:

`HOUSTON_PRIVATE_MEDIA_ROOT=/tmp/houston-private-media`

See [Known limitations V1 — private media](#known-limitations-v1--private-media).

---

## Service: `celery-beat` (mandatory)

| Field | Value |
|---|---|
| Source | Same GitHub repository |
| Root Directory | `/` |
| Config File | `/infra/railway/celery-beat/railway.toml` |
| Dockerfile | `infra/docker/api/Dockerfile` |
| Visibility | Private |
| Depends on | `postgres`, `redis` |

### Start command

```toml
startCommand = "cd /app/apps/api && uv run celery -A config beat -l info --scheduler celery.beat:PersistentScheduler --schedule /var/lib/celerybeat/celerybeat-schedule"
```

### Volume (beat schedule)

| Mount path | Purpose |
|---|---|
| `/var/lib/celerybeat` | Persistent Celery Beat schedule file |

Without this volume, beat schedule resets on redeploy.

### Health / verification

No HTTP healthcheck. Verify in logs:

* Beat scheduler started
* Periodic tasks registered (horizon materialization, chat purge, upload TTL, stuck observation recovery)

**Celery Beat is not optional** in prod-test.

---

## Service: `postgres`

| Field | Value |
|---|---|
| Type | Railway PostgreSQL plugin |
| Visibility | Private network only |
| SSL | `POSTGRES_SSLMODE=require` |

### Migrations

Run via `api-web` pre-deploy only. Do not run migrations from workers.

### Backup (before external testers)

* Enable Railway Postgres daily backups (or equivalent `pg_dump` cron)
* Document restore: new Postgres instance → restore dump → update `POSTGRES_*` on all services → redeploy

---

## Service: `redis`

| Field | Value |
|---|---|
| Type | Railway Redis plugin |
| Visibility | Private network only — **never public** |

Map one Railway Redis URL to Houston logical DBs 0–3 (see [`railway_variables.md`](railway_variables.md)).

---

## Known limitations V1 — private media

Railway **cannot attach the same volume to multiple services**.

| Service | Storage |
|---|---|
| `api-web` | Persistent volume at `HOUSTON_PRIVATE_MEDIA_ROOT` |
| `celery-worker` | Ephemeral filesystem only |

**What works in V1:**

* Photo upload and API-authorized read via `api-web`

**What is not fully guaranteed in V1:**

* Celery tasks that delete files on disk (`cleanup_expired_uploads`, `delete_all_observation_media`) run on the worker without access to the `api-web` volume. Purge/delete cross-service may leave **orphan files** on the api-web volume or fail silently on the worker.

Do not present cross-service media purge as fully guaranteed until object storage (future PR, out of scope PR5).

---

## WebSocket

Documented URLs (replace `<railway-domain>` and `<uuid>`):

```txt
wss://<railway-domain>/ws/v1/establishments/<uuid>/chat/
wss://<railway-domain>/ws/v1/establishments/<uuid>/realtime/
```

Full authenticated sessions require WS tickets (app flow). Routing smoke: `/ws/*` must **not** return SPA `index.html`.

---

## Upload limits

| Setting | Value |
|---|---|
| `HOUSTON_OBSERVATION_PHOTO_MAX_BYTES` | 10 MiB (default) |
| `HOUSTON_TRANSCRIPTION_AUDIO_MAX_BYTES` | 10 MiB (default) |
| nginx `client_max_body_size` | `12m` ([`infra/docker/railway/nginx.conf`](../../infra/docker/railway/nginx.conf)) |

---

## Logs

View per service in the Railway dashboard:

| Service | What to look for |
|---|---|
| `api-web` | Daphne/nginx start, `check --deploy`, HTTP errors, pre-deploy migrate output |
| `celery-worker` | Worker ready, task execution, task failures |
| `celery-beat` | Scheduler tick, periodic task dispatch |

Never paste secrets, tokens, raw observation text, or private media paths in tickets.

---

## Restart and redeploy

| Change type | Action |
|---|---|
| Env var update | Update Railway variables → redeploy affected services (`api-web`, `celery-worker`, `celery-beat`) |
| Code change | Push to connected branch → Railway rebuilds from Dockerfile → redeploy |
| Postgres / Redis | Managed plugins; restart via dashboard if needed; app services reconnect |
| Volume on `api-web` | Brief downtime on redeploy (Railway serializes volume mounts) |

No bind-mount `.env` in prod-test — all config via Railway variables.

---

## Rollback (minimal)

1. Railway dashboard → `api-web` (or affected service) → **Deployments**
2. Select the last known-good deployment → **Redeploy** / rollback to previous image
3. Repeat for `celery-worker` and `celery-beat` if they were deployed together
4. If a bad migration shipped: restore Postgres from backup or run reverse migration manually before rollback

---

## Smoke tests (manual, post-deploy)

Run the readonly script from the repository root (single source of truth for infra curls):

```bash
BASE_URL=https://<railway-domain> ./scripts/smoke/readonly.sh
```

Local prod-test: `BASE_URL=http://localhost:8080` after `make up-prod-test`. See [`scripts/smoke/readonly.sh`](../../scripts/smoke/readonly.sh) and [`railway_smoke_checklist.md`](railway_smoke_checklist.md) for manual worker/beat/media checks.

---

## Validation gates (pre-merge / pre-first-deploy)

```bash
make backend-check
make web-check
make backend-deploy-check
```

---

## Explicit prohibitions

| Forbidden | Notes |
|---|---|
| Optional worker/beat in prod-test docs | PR rejection criterion |
| `DJANGO_DEBUG=1` | Use `0` |
| Nixpacks / Procfile | Dockerfile only |
| Cloudflare in critical path | Railway HTTPS for V1 |
| S3 / R2 / MinIO in PR5 | Future object storage |
| Migrations in worker/beat start | pre-deploy `api-web` only |
| `import_business_unit_catalog` in pre-deploy | Manual post-migrate |

---

## Related documents

* [`prod_test_runbook.md`](prod_test_runbook.md) — operator hub (day-0 → sign-off)
* [`railway_variables.md`](railway_variables.md) — variable mapping and per-service matrix
* [`railway_architecture.md`](railway_architecture.md) — architecture overview
* [`railway_security.md`](railway_security.md) — secrets and `check --deploy`
* [`prod_test_decisions.md`](prod_test_decisions.md) — frozen decisions
* [`railway_static_frontend.md`](railway_static_frontend.md) — local same-origin validation (PR3)
