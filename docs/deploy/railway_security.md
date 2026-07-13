# Railway Security — Prod-test V1

Operational security contract for Houston prod-test on Railway. Architecture context: [`railway_architecture.md`](railway_architecture.md).

## Goal

With `DJANGO_DEBUG=0`, Houston must refuse to start or pass deployment checks when secrets, hosts, CSRF, auth salts, OpenAI, or private media are misconfigured.

Run before first deploy and after any security-related env change:

```bash
DJANGO_DEBUG=0 python manage.py check --deploy
```

From the repo root (Docker api container):

```bash
make backend-deploy-check
```

## Generate secrets

Generate one independent random value per secret. Example:

```bash
openssl rand -hex 32
```

Never reuse the same value across:

* `DJANGO_SECRET_KEY`
* `HOUSTON_AUTH_TOKEN_PEPPER`
* `HOUSTON_AUTH_TOKEN_SALT`
* `HOUSTON_CHAT_WS_TICKET_SALT`
* `HOUSTON_REALTIME_WS_TICKET_SALT`

`HOUSTON_AUTH_TOKEN_PEPPER` must be **explicitly set** and **distinct** from `DJANGO_SECRET_KEY`.

Forbidden placeholders:

* `replace-me-for-local-dev`
* `replace-me-for-local-prod-test`
* empty values

## Required Railway variables (prod-test)

Set on `api-web`, `celery-worker`, and `celery-beat` unless noted otherwise.

| Variable | Required | Notes |
|---|---|---|
| `DJANGO_DEBUG` | yes | Must be `0` |
| `DJANGO_SECRET_KEY` | yes | Strong random secret |
| `DJANGO_ALLOWED_HOSTS` | yes | Public Railway domain(s) |
| `CSRF_TRUSTED_ORIGINS` | yes | `https://<railway-domain>` |
| `HOUSTON_AUTH_TOKEN_PEPPER` | yes | Explicit, distinct from secret key |
| `HOUSTON_AUTH_TOKEN_SALT` | yes | Not the dev default |
| `HOUSTON_CHAT_WS_TICKET_SALT` | yes | Not the dev default |
| `HOUSTON_REALTIME_WS_TICKET_SALT` | yes | Not the dev default |
| `OPENAI_API_KEY` | yes | Required when AI providers are `openai` |
| `HOUSTON_PRIVATE_MEDIA_ROOT` | yes (`api-web`, `celery-worker`) | Writable shared path |
| `POSTGRES_*` | yes | From Railway Postgres plugin |
| `REDIS_URL`, `CELERY_*`, `HOUSTON_CACHE_REDIS_URL` | yes | Private Redis only |
| `HOUSTON_ENABLE_API_DOCS` | no | Default off in prod-test |
| `HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS` | no | **Local only — never on Railway** |
| `HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS` | no | **Local only — never on Railway** |

Full service matrix: [`railway_architecture.md`](railway_architecture.md).

## HTTPS and proxy behavior

Railway terminates HTTPS at the edge. Houston expects:

* `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
* `SECURE_SSL_REDIRECT = False` (redirect handled by Railway)
* secure cookies enabled when `DJANGO_DEBUG=0`

Public CSRF origins must use `https://`.

## Local prod-test HTTP exception

`make up-prod-test` may use `http://localhost:8080` for same-origin local validation.

This is allowed only with explicit local flags in [`docker-compose.prod-test.yml`](../../docker-compose.prod-test.yml):

* `HOUSTON_ALLOW_INSECURE_LOCAL_CSRF_ORIGINS=1`
* `HOUSTON_ALLOW_LOCAL_ALLOWED_HOSTS=1`

Rules:

* HTTP is allowed only for `localhost` / `127.0.0.1`
* never for a public domain
* never set these flags on Railway

## API docs in prod-test

`/api/schema/` and `/api/docs/` are **disabled by default** when `DJANGO_DEBUG=0`.

Enable only for a deliberate, time-boxed need:

```bash
HOUSTON_ENABLE_API_DOCS=1
```

OpenAPI generation for CI/contracts is unchanged:

```bash
make backend-schema
```

## Startup guard (api service)

When `DJANGO_DEBUG=0`, [`infra/docker/api/entrypoint.sh`](../../infra/docker/api/entrypoint.sh) runs `python manage.py check --deploy` before Daphne starts.

Celery worker and beat do not use this entrypoint today. Strict startup coverage for all backend services will be validated in **PR5**.

## What the gate checks

With `DJANGO_DEBUG=0`, custom checks fail when:

* secret key is empty or a local placeholder
* allowed hosts are empty or local-only without the local exception flag
* CSRF trusted origins are empty or use forbidden HTTP origins
* auth pepper is missing, placeholder, or equal to the Django secret
* auth / WebSocket salts still use dev defaults
* OpenAI provider is active without `OPENAI_API_KEY`
* private media root is empty or not writable

With `DJANGO_DEBUG=1`, dev remains permissive.

## Related documents

* [`railway_architecture.md`](railway_architecture.md)
* [`smoke_checklist.md`](smoke_checklist.md)
* [`.env.prod-test.example`](../../.env.prod-test.example)
