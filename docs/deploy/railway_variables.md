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

## Checklist before first traffic

1. [ ] All secrets generated and distinct
2. [ ] `DJANGO_DEBUG=0`
3. [ ] `DJANGO_ALLOWED_HOSTS` includes public domain + `healthcheck.railway.app`
4. [ ] `CSRF_TRUSTED_ORIGINS` includes `https://<public-domain>`
5. [ ] `POSTGRES_SSLMODE=require`
6. [ ] Redis URLs mapped to DBs 0–3
7. [ ] `make backend-deploy-check` passes locally
8. [ ] `celery-worker` and `celery-beat` deployed and running
9. [ ] `import_business_unit_catalog` run manually after migrate

---

## Related

* [`railway_deploy_contract.md`](railway_deploy_contract.md) — services, commands, smoke tests
* [`railway_architecture.md`](railway_architecture.md) — architecture
* [`apps/api/config/settings.py`](../../apps/api/config/settings.py) — all env reads
