# Railway Variables — Prod-test V1

Reference for Houston environment variables on Railway. Operational playbook: [`railway_deploy_contract.md`](railway_deploy_contract.md). Security: [`railway_security.md`](railway_security.md). Template: [`.env.prod-test.example`](../../.env.prod-test.example).

Set variables in the Railway dashboard (or Railway CLI). **Never commit real secrets.**

---

## Domain and healthcheck

After generating the public Railway domain for `api-web`:

```bash
DJANGO_ALLOWED_HOSTS=<railway-public-domain>,healthcheck.railway.app
CSRF_TRUSTED_ORIGINS=https://<railway-public-domain>
```

| Variable | Example | Notes |
|---|---|---|
| `DJANGO_ALLOWED_HOSTS` | `houston-prod-test.up.railway.app,healthcheck.railway.app` | Comma-separated; no spaces. Include `healthcheck.railway.app` so Railway healthchecks do not get `400 DisallowedHost`. |
| `CSRF_TRUSTED_ORIGINS` | `https://houston-prod-test.up.railway.app` | HTTPS only; match the public origin |

For multiple domains (e.g. Railway default + custom): add all to `DJANGO_ALLOWED_HOSTS`; add all `https://` origins to `CSRF_TRUSTED_ORIGINS`.

---

## PostgreSQL (Railway plugin → Houston)

Railway Postgres exposes reference variables (names may vary by plugin version). Map to Houston names on **all** backend services (`api-web`, `celery-worker`, `celery-beat`):

| Houston variable | Source |
|---|---|
| `POSTGRES_DB` | Railway `PGDATABASE` or plugin reference |
| `POSTGRES_USER` | Railway `PGUSER` |
| `POSTGRES_PASSWORD` | Railway `PGPASSWORD` |
| `POSTGRES_HOST` | Railway `PGHOST` (private hostname) |
| `POSTGRES_PORT` | Railway `PGPORT` (usually `5432`) |
| `POSTGRES_SSLMODE` | `require` (prod-test) |

Use Railway **variable references** (`${{Postgres.PGHOST}}`) where supported to avoid manual copy/paste drift.

---

## Redis (Railway plugin → Houston)

Railway provides one Redis URL. Split logical databases (same pattern as local [`docker-compose.yml`](../../docker-compose.yml)):

| Houston variable | Typical mapping | Purpose |
|---|---|---|
| `REDIS_URL` | `redis://<user>:<pass>@<host>:<port>/0` | Django Channels |
| `CELERY_BROKER_URL` | `redis://…/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://…/2` | Celery results |
| `HOUSTON_CACHE_REDIS_URL` | `redis://…/3` | Throttle / cache (explicit recommended in prod) |

**Do not expose Redis publicly.** Private network only.

---

## Secrets (manual — generate before deploy)

Generate independent random values (`openssl rand -hex 32`). Set on `api-web`, `celery-worker`, and `celery-beat` unless noted.

| Variable | Required | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes | Strong random secret |
| `DJANGO_DEBUG` | yes | Must be `0` |
| `HOUSTON_AUTH_TOKEN_PEPPER` | yes | Distinct from `DJANGO_SECRET_KEY` |
| `HOUSTON_AUTH_TOKEN_SALT` | yes | Not dev default |
| `HOUSTON_CHAT_WS_TICKET_SALT` | yes | Not dev default |
| `HOUSTON_REALTIME_WS_TICKET_SALT` | yes | Not dev default |
| `OPENAI_API_KEY` | yes | Required when AI providers are `openai` |

Forbidden placeholders: `replace-me-for-local-dev`, empty values.

---

## Per-service variable matrix

| Variable / group | `api-web` | `celery-worker` | `celery-beat` |
|---|---|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` | yes | yes | yes |
| `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | yes | yes | yes |
| `POSTGRES_*` | yes | yes | yes |
| `REDIS_URL`, `CELERY_*`, `HOUSTON_CACHE_REDIS_URL` | yes | yes | yes |
| Auth salts / `OPENAI_API_KEY` | yes | yes | yes |
| AI provider vars (`HOUSTON_AI_*`) | yes | yes | yes |
| `HOUSTON_PRIVATE_MEDIA_ROOT` | yes — `/app/apps/api/private_media` | yes — `/tmp/houston-private-media` (ephemeral) | no |
| `HOUSTON_REGISTRATION_INVITE_CODES` | yes | no | no |
| `PORT` | injected by Railway | n/a | n/a |
| `HOUSTON_ENABLE_API_DOCS` | optional (`0` default prod-test) | optional | optional |
| `HOUSTON_LOG_LEVEL` | optional (`INFO`) | optional | optional |
| `CELERY_WORKER_CONCURRENCY` | no | **yes** | no |

### Never set on Railway

| Variable | Reason |
|---|---|
| `HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS` | Local prod-test only |
| `HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS` | Local prod-test only |
| `VITE_*` API URLs | Same-origin prod-test; no API secret in frontend build vars |

---

## Private media and volumes

| Service | `HOUSTON_PRIVATE_MEDIA_ROOT` | Volume |
|---|---|---|
| `api-web` | `/app/apps/api/private_media` | Railway volume at same mount path |
| `celery-worker` | `/tmp/houston-private-media` | None (ephemeral; deploy-check writable path only) |
| `celery-beat` | not required | N/A |

See [Known limitations V1](railway_deploy_contract.md#known-limitations-v1--private-media) in the deploy contract.

---

## Celery beat volume

No env var — mount a Railway volume on `celery-beat` at `/var/lib/celerybeat`. Schedule file: `/var/lib/celerybeat/celerybeat-schedule`.

---

## Upload limits

Optional overrides (defaults are 10 MiB each):

| Variable | Default |
|---|---|
| `HOUSTON_OBSERVATION_PHOTO_MAX_BYTES` | `10485760` |
| `HOUSTON_TRANSCRIPTION_AUDIO_MAX_BYTES` | `10485760` |

nginx on `api-web` allows `12m` request bodies ([`infra/docker/railway/nginx.conf`](../../infra/docker/railway/nginx.conf)).

---

## Registration and onboarding

| Variable | Service | Notes |
|---|---|---|
| `HOUSTON_REGISTRATION_INVITE_CODES` | `api-web` only | Comma-separated codes per onboarding policy |
| `HOUSTON_DIRECTOR_INVITATION_TTL_DAYS` | `api-web` | Default `7` |

---

## Throttling (prod defaults apply when unset)

| Variable | Default when unset (`DJANGO_DEBUG=0`) |
|---|---|
| `HOUSTON_AUTH_THROTTLE_ENABLED` | `true` |
| `HOUSTON_THROTTLE_AUTH_LOGIN` | `10/minute` |
| `HOUSTON_THROTTLE_AUTH_REFRESH` | `30/minute` |
| `HOUSTON_THROTTLE_AUTH_REGISTER` | `5/hour` |

---

## Celery worker concurrency (`celery-worker` only)

`CELERY_WORKER_CONCURRENCY` is **required** on `celery-worker` only. The Railway `startCommand` validates it in shell **before** Celery starts; do not set it on `api-web` or `celery-beat`.

| Variable | Service | Required | Notes |
|---|---|---|---|
| `CELERY_WORKER_CONCURRENCY` | `celery-worker` | yes | Positive decimal integer (digits only, no leading zero). Passed to `celery worker --concurrency`. |

### Shell validation (start command)

The worker `startCommand` rejects, with exit 1 **before** Celery launches:

| Input | Result |
|---|---|
| unset / empty | `CELERY_WORKER_CONCURRENCY is required` |
| non-digits (`abc`, `-1`, spaces) | `must contain only decimal digits` |
| `0`, `00`, `01` (leading zero) | `must be greater than zero` |

The shell check validates **form only** (required, digits, > 0, no leading zero). It does **not** cap an excessively large value — choose `C` from sizing below.

### Celery default trap (why the variable is mandatory)

Without `--concurrency`, Celery 5.6 defaults to `os.cpu_count()` (e.g. **48 prefork** on 8 vCPU Railway). Worse: `--concurrency=0` is treated as falsy and **falls back to the same CPU-based default**. The shell validation prevents ever passing `0` to Celery.

Verify after deploy: worker logs must show `concurrency: <C> (prefork)` where `<C>` equals `CELERY_WORKER_CONCURRENCY`, not the host CPU count.

### Sizing procedure (isolated staging — not production)

Choose `C` **before** setting the variable on production `celery-worker`:

1. Use a **dedicated Railway test project** or temporary cloned `celery-worker` service on a **non-production branch** — fully isolated broker, PostgreSQL, and data from production.
2. **Do not** connect sizing experiments to the production broker, production Postgres, or production datasets.
3. **Do not** start a second Celery worker via SSH inside the production container.
4. Measure memory at representative burst load by **successive redeploys** with `CELERY_WORKER_CONCURRENCY` = 1, 2, 4, 8, … — **one active worker** on the test broker at a time.
5. Model: `M_total(C) = M_main + C × M_child_idle + C × Δ_task_active + headroom`; Select the lowest `C` that meets the measured throughput and latency objectives while keeping cgroup/container memory below the Railway limit with the required headroom and respecting PostgreSQL and OpenAI constraints.
6. Set the chosen value on production `celery-worker` **before or when** merging the `startCommand` that requires this variable.

### Rollback

If concurrency causes OOM or instability: revert to the **last explicitly validated** `CELERY_WORKER_CONCURRENCY` value — never rely on removing the variable (that crashes the worker) and never expect an automatic fallback away from an explicit `C`.

Phase 2 (`CELERY_WORKER_PREFETCH_MULTIPLIER`) is out of scope here.

---

## Checklist before first traffic

1. [ ] All secrets generated and distinct
2. [ ] `DJANGO_DEBUG=0`
3. [ ] `DJANGO_ALLOWED_HOSTS` includes public domain + `healthcheck.railway.app`
4. [ ] `CSRF_TRUSTED_ORIGINS` includes `https://<public-domain>`
5. [ ] `POSTGRES_SSLMODE=require`
6. [ ] Redis URLs mapped to DBs 0–3
7. [ ] `make backend-deploy-check` passes locally
8. [ ] `CELERY_WORKER_CONCURRENCY` set on `celery-worker` (positive integer, chosen from isolated staging sizing)
9. [ ] `celery-worker` and `celery-beat` deployed and running; worker logs show `concurrency: <C> (prefork)` matching the variable
10. [ ] `import_business_unit_catalog` run manually after migrate

---

## Related

* [`railway_deploy_contract.md`](railway_deploy_contract.md) — services, commands, smoke tests
* [`railway_architecture.md`](railway_architecture.md) — architecture
* [`apps/api/config/settings.py`](../../apps/api/config/settings.py) — all env reads
