# Railway Deploy Contract — Prod-test V1

Operational playbook for deploying Houston on Railway. Architecture context: [`railway_architecture.md`](railway_architecture.md). Variables: [`railway_variables.md`](railway_variables.md). Config wiring: [`infra/railway/README.md`](../../infra/railway/README.md).

`celery-worker` and `celery-beat` are **mandatory** in prod-test — not optional.

## Project topology

Same-origin public routing on `https://<railway-domain>`. Service tree (api-web public + private worker/beat/postgres/redis + S3 media): [`railway_architecture.md`](railway_architecture.md#architecture-option-a-only).

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

## Build triggers (Watch Paths)

Each service's `railway.toml` defines `watchPatterns` under `[build]`. Do not paste the arrays here: [`infra/railway/README.md`](../../infra/railway/README.md) and `infra/railway/*/railway.toml`.

Railway evaluates patterns from the repository root (`/`). Changes under `/docs/**` or `/.cursor/**` skip deployment.

### Trigger matrix

| Change | `api-web` | `celery-worker` | `celery-beat` |
|---|---:|---:|---:|
| `/apps/web/**` | Yes | No | No |
| `/contracts/operational-realtime-invalidation.json` | Yes | Yes | Yes |
| `/apps/api/**` | Yes | Yes | Yes |
| `/infra/docker/railway/**` | Yes | No | No |
| `/infra/docker/api/**` | No | Yes | Yes |
| `/infra/railway/api-web/**` | Yes | No | No |
| `/infra/railway/celery-worker/**` | No | Yes | No |
| `/infra/railway/celery-beat/**` | No | No | Yes |
| `/pyproject.toml`, `/uv.lock` | Yes | Yes | Yes |
| `/.dockerignore` | Yes | Yes | Yes |
| `/docs/**`, `/.cursor/**`, `/README.md` | No | No | No |

`api-web` does **not** watch `/infra/docker/api/**`. Worker and beat do **not** watch frontend or Railway edge paths.

### Validation (post-merge)

Do not use artificial test commits on the production branch. Prefer a Railway test environment connected to a non-production branch, or observe real pushes after merge:

| Scenario | Expected |
|---|---|
| Change under `/docs/**` only | 0 deploys |
| Change under `/apps/web/**` only | `api-web` only |
| Change under `/apps/api/**` only | all 3 services |
| Change under `/infra/docker/api/**` only | worker + beat only |

Rollback: remove `watchPatterns` from the affected `railway.toml` files.

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

The image includes: production Python venv (`/opt/venv`), production SPA build (`apps/web/dist`), nginx edge config.

Images are **multi-stage**: a `python-builder` stage runs `uv sync` with **uv `0.11.16`** (`ghcr.io/astral-sh/uv:0.11.16`) and `build-essential`; the production runtime copies only `/opt/venv` and application code — **no `uv`, `curl`, `gcc`, or `make`** in the deployed image. Local dev images built with `UV_SYNC_DEV=true` (see [`docker-compose.yml`](../../docker-compose.yml)) intentionally retain `uv` for `uv run` in Compose/Makefile.

### Pre-deploy (migrations only)

Configured in [`infra/railway/api-web/railway.toml`](../../infra/railway/api-web/railway.toml):

```toml
preDeployCommand = "/bin/sh -c 'cd /app/apps/api && /opt/venv/bin/python manage.py migrate --noinput --verbosity 2'"
```

* Runs in a **separate container** before the new deployment goes live.
* **Volumes are not mounted** during pre-deploy — migrations are DB-only (safe).
* **Workers and beat do not run migrations.**

If pre-deploy fails: fix the error, or run migrate manually (Railway shell / one-off) before accepting traffic.

### Organizational owners gate (before enabling multi-owner / org-owner invites)

Run against the target database **before** relying on organizational owner invite / deactivate / reactivate in that environment:

```bash
make preflight-organizational-owners
# equivalent: manage.py preflight_organizational_owners --fail-on-issues
```

* Fails on owner status mixes, non-owner conflicts, and missing-owner gaps.
* Homogeneous missing-owner gaps only: `make repair-organizational-owners ARGS='--apply'`, then re-run preflight until green.
* Status mixes / non-owner conflicts: **block deploy / feature activation** until manual data correction. Repair does not align statuses.

### Post-migrate bootstrap (manual)

After first migrate (or schema change), run **once** manually:

```bash
cd /app/apps/api && /opt/venv/bin/python manage.py import_business_unit_catalog
```

Use Railway service shell or `railway run` against `api-web`. Not automated in pre-deploy.

### Start command

```toml
startCommand = "/app/infra/docker/railway/start-api-web.sh"
drainingSeconds = 20
```

The script ([`infra/docker/railway/start-api-web.sh`](../../infra/docker/railway/start-api-web.sh)):

* Sets `PORT="${PORT:-8080}"`
* Runs `/opt/venv/bin/python manage.py check --deploy` when `DJANGO_DEBUG=0`
* Starts **Daphne** via `/opt/venv/bin/daphne` on `127.0.0.1:8000` (HTTP + WebSocket)
* Starts **nginx** on `0.0.0.0:$PORT` (Railway edge)
* Routes `/api/*` and `/ws/*` to Daphne; `/*` to SPA static
* Exits 0 on SIGTERM/SIGINT (Railway teardown); exits non-zero only if Daphne or nginx dies without a shutdown signal
* `drainingSeconds = 20` is the Railway grace ceiling before SIGKILL, not a fixed sleep

No `$PORT` logic in `railway.toml` — only in the start script.

### Healthcheck

| Setting | Value |
|---|---|
| Railway `healthcheckPath` | `/api/v1/health/` |
| Expected response | `200` + `{"status":"ok"}` |
| Proves | API process + nginx routing only |

Railway queries from hostname `healthcheck.railway.app` — include it in `DJANGO_ALLOWED_HOSTS` (see [`railway_variables.md`](railway_variables.md)).

### Volume (not media truth)

The `api-web` volume at `/app/apps/api/private_media` (`HOUSTON_PRIVATE_MEDIA_ROOT`) is **not** prod-test media truth. Prod-test uses `HOUSTON_PRIVATE_MEDIA_BACKEND=s3` with the same `HOUSTON_S3_*` values on `api-web` and `celery-worker`. `start-api-web.sh` creates the media directory only when backend=filesystem.

A leftover volume may still exist from historical filesystem deploys. Railway volumes mount as root; the start script `chown`s that directory when it is used.

Horizontal scale of `api-web` is no longer blocked by a single media volume when backend=s3.

### Domain

1. Enable Railway Public Networking on `api-web`.
2. Generate or attach a domain (`*.railway.app` or Railway custom domain).
3. Set `DJANGO_ALLOWED_HOSTS` and `HOUSTON_CLIENT_ORIGINS` (see variables doc).

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

Same multi-stage build as `api-web` Python layer: **uv `0.11.16`** and `build-essential` in the builder only; production runtime without `uv`/`curl`/`gcc`/`make`.

### Start command

```toml
startCommand = "/bin/sh -c 'if [ -z \"${CELERY_WORKER_CONCURRENCY:-}\" ]; then echo \"CELERY_WORKER_CONCURRENCY is required\" >&2; exit 1; fi; case \"$CELERY_WORKER_CONCURRENCY\" in *[!0-9]*) echo \"CELERY_WORKER_CONCURRENCY must contain only decimal digits\" >&2; exit 1;; 0|0*) echo \"CELERY_WORKER_CONCURRENCY must be greater than zero\" >&2; exit 1;; esac; exec /opt/venv/bin/celery -A config worker -l info -n houston-worker@%h --concurrency=\"$CELERY_WORKER_CONCURRENCY\"'"
```

* `CELERY_WORKER_CONCURRENCY` is **required** on this service (see [`railway_variables.md`](railway_variables.md#celery-worker-concurrency-celery-worker-only)).
* Shell validates presence, decimal digits only, value > 0, no leading zero — **before** `exec` (so Celery never receives `--concurrency=0`, which would fall back to CPU-count default).
* `exec` replaces the shell so SIGTERM reaches the Celery process for graceful shutdown.

### Health / verification

No HTTP healthcheck. Verify in Railway logs:

* Startup banner includes `concurrency: <C> (prefork)` where `<C>` matches `CELERY_WORKER_CONCURRENCY` (not host CPU count, e.g. not `48` unless explicitly set).
* Missing or invalid `CELERY_WORKER_CONCURRENCY` → shell error on stderr, exit 1, **no** Celery worker process — crash loop until the variable is fixed.
* `celery@houston-worker` ready message
* Worker processes tasks when observations are submitted

**Sizing:** choose `<C>` via redeployments on an **isolated** Railway test service (dedicated broker/Postgres, no production data). Do **not** spawn a second worker via SSH on production. See variables doc.

**Prod-test is broken** if the worker is down: observation processing and AI signal generation stop.

### Volume

**No private-media volume on the worker.** Prod-test media is S3 (same `HOUSTON_S3_*` as `api-web`).

Historical filesystem deploys used an ephemeral writable path for deploy checks only:

`HOUSTON_PRIVATE_MEDIA_ROOT=/tmp/houston-private-media`

That worker `/tmp` vs `api-web` volume split is **not** the current prod-test S3 mode. See [Known limitations V1 — private media](#known-limitations-v1--private-media).

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
startCommand = "/opt/venv/bin/celery -A config beat -l info --scheduler celery.beat:PersistentScheduler --schedule /var/lib/celerybeat/celerybeat-schedule"
```

### Volume (beat schedule)

| Mount path | Purpose |
|---|---|
| `/var/lib/celerybeat` | Persistent Celery Beat schedule file |

Without this volume, beat schedule resets on redeploy.

**Singleton:** run exactly **one** Celery Beat replica (`numReplicas = 1` in the Railway dashboard). Do not scale Beat horizontally — duplicate schedulers dispatch the same periodic tasks twice.

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

This section describes the **historical filesystem** layout: Railway **cannot attach the same volume to multiple services**. It is **not** the current prod-test mode (`HOUSTON_PRIVATE_MEDIA_BACKEND=s3`, same bucket on `api-web` and `celery-worker`).

| Service | Historical filesystem storage |
|---|---|
| `api-web` | Persistent volume at `HOUSTON_PRIVATE_MEDIA_ROOT` |
| `celery-worker` | Ephemeral filesystem only (`/tmp`) |

**What worked on filesystem V1:**

* Photo upload and API-authorized read via `api-web`

**What was not fully guaranteed on filesystem V1:**

* Celery tasks that delete files on disk (`cleanup_expired_uploads`, `delete_all_observation_media`) ran on the worker without access to the `api-web` volume. Purge/delete cross-service could leave **orphan files** on the api-web volume or fail silently on the worker.

Do not present that volume split as the current prod-test media architecture.

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
| `celery-worker` | Worker ready, `concurrency: <C> (prefork)` banner, task execution, task failures |
| `celery-beat` | Scheduler tick, periodic task dispatch |

Never paste secrets, tokens, raw observation text, or private media paths in tickets.

---

## Restart and redeploy

| Change type | Action |
|---|---|
| Env var update | Update Railway variables → redeploy affected services (`api-web`, `celery-worker`, `celery-beat`) |
| Code change (push) | Railway rebuilds only services whose `watchPatterns` match changed paths (see [Build triggers](#build-triggers-watch-paths)); otherwise deploy is skipped |
| Postgres / Redis | Managed plugins; restart via dashboard if needed; app services reconnect |
| Volume on `api-web` | Brief downtime on redeploy (Railway serializes volume mounts) |
| Volume on `celery-beat` | Brief downtime on redeploy; schedule persists via `/var/lib/celerybeat` mount |

No bind-mount `.env` in prod-test — all config via Railway variables.

---

## Rollback (minimal)

1. Railway dashboard → `api-web` (or affected service) → **Deployments**
2. Select the last known-good deployment → **Redeploy** / rollback to previous image
3. Repeat for `celery-worker` and `celery-beat` if they were deployed together
4. If a bad migration shipped: restore Postgres from backup or run reverse migration manually before rollback

**`celery-worker` concurrency:** if a new `CELERY_WORKER_CONCURRENCY` causes OOM or instability, set the variable back to the **last explicitly validated** value and redeploy — do not remove the variable (startup fails) and do not expect Celery to fall back to a safe default (omitting `--concurrency` or passing `0` uses CPU-count prefork, e.g. 48).

---

## Smoke tests (manual, post-deploy)

Run the readonly script from the repository root (single source of truth for infra curls):

```bash
BASE_URL=https://<railway-domain> ./scripts/smoke/readonly.sh
```

Local prod-test: `BASE_URL=http://localhost:8080` after `make up-prod-test`. See [`scripts/smoke/readonly.sh`](../../scripts/smoke/readonly.sh) and [`smoke_checklist.md`](smoke_checklist.md) for manual worker/beat/media checks.

---

## Validation gates (pre-merge / pre-first-deploy)

```bash
make backend-check
make web-check
make backend-deploy-check
# Before enabling organizational owner workflows on an environment with data:
make preflight-organizational-owners
```

CI also runs `manage.py check --deploy` in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) (mirror of `make backend-deploy-check`). It fails on deploy **errors**, not necessarily on warnings — no `--fail-level WARNING`.

---

## Wait for CI

Railway **waits for GitHub workflows triggered on the commit** before starting a build. No manual list of GitHub job names is configured on the Railway side — Railway waits for whichever workflows GitHub runs for that commit.

| Workflow | Trigger | Waited by Railway |
|---|---|---|
| [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | **Always** (push/PR, no `paths` filter) | Yes — when triggered on the commit |
| [`.github/workflows/docker-smoke.yml`](../../.github/workflows/docker-smoke.yml) | Only when a filtered path changes on the commit | Yes **when triggered**; not present on commits that do not match |

Consequences:

* Docs-only commits (`/docs/**`): `ci.yml` still runs; Railway waits for it to pass.
* Commits touching `infra/docker/api/**` or `infra/docker/railway/**`: Railway waits for **both** `ci.yml` and `docker-smoke.yml`.
* In GitHub branch protection, required checks are the jobs from `ci.yml` (`backend-tests`, `frontend-tests`, `docs-check`). `docker-smoke.yml` is path-filtered and is not a required branch-protection check, but Railway still blocks if that workflow is triggered on the commit and fails.

### Phase A — test environment (required before prod)

1. Create or reuse a **Railway test project** or clone services connected to a **non-production GitHub branch** (e.g. `railway-test`).
2. **Enable Wait for CI** on all three test services only.
3. Push with green CI → build starts after all workflows triggered on the commit complete.
4. Push touching `infra/docker/api/**` or `infra/docker/railway/**` → confirm Railway waits for `ci.yml` **and** `docker-smoke.yml`.
5. Deliberately fail CI on the test branch → Railway build must not start or promote.
6. **Never** deliberately fail CI on the branch connected to **production**.

### Phase B — production (after Phase A validated)

1. Note the deploy baseline before changing settings.
2. Check current Wait for CI state on `api-web`, `celery-worker`, and `celery-beat` prod services.
3. **Enable** Wait for CI on all three prod services after Phase A validation.
4. Observe the first real prod push: green CI → deploy; note the additional wait time (GitHub workflow completion, not a Docker build regression).

### Branch protection vs Railway

| Scope | GitHub branch protection | Railway Wait for CI |
|---|---|---|
| [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | Required jobs: `backend-tests`, `frontend-tests`, `docs-check` | Waits for the workflow when triggered on the commit |
| [`.github/workflows/docker-smoke.yml`](../../.github/workflows/docker-smoke.yml) | Not required (path-filtered workflow) | Waits for the workflow when triggered on the commit |

Railway does not expose a manual checklist of GitHub job names — only workflows triggered on the commit matter.

Railway remains the CD system — no GitHub deploy workflow.

Rollback: disable Wait for CI (test then prod); revert workflow changes if needed.

---

## Explicit prohibitions

| Forbidden | Notes |
|---|---|
| Optional worker/beat in prod-test docs | PR rejection criterion |
| `DJANGO_DEBUG=1` | Use `0` |
| Nixpacks / Procfile | Dockerfile only |
| Cloudflare in critical path | Railway HTTPS for V1 |
| Invented object storage for this playbook | Current prod-test uses S3 (see [`railway_variables.md`](railway_variables.md)) |
| Migrations in worker/beat start | pre-deploy `api-web` only |
| `import_business_unit_catalog` in pre-deploy | Manual post-migrate |

---

## Related documents

* [`prod_test_runbook.md`](prod_test_runbook.md) — operator hub (day-0 → sign-off)
* [`railway_variables.md`](railway_variables.md) — variable mapping and per-service matrix
* [`railway_architecture.md`](railway_architecture.md) — architecture overview
* [`railway_security.md`](railway_security.md) — secrets and `check --deploy`
* [`smoke_checklist.md`](smoke_checklist.md) — unified smoke
* Local same-origin: `docker-compose.prod-test.yml` + `make up-prod-test`
