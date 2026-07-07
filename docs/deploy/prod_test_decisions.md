# Prod-test V1 Decisions

This document freezes the prod-test V1 architecture contract. Operational detail lives in [`railway_architecture.md`](railway_architecture.md). Environment variables are listed in [`.env.prod-test.example`](../../.env.prod-test.example).

## Hosting decision

Prod-test V1 runs on **Railway**.

Railway hosts the runtime:

* Django / Daphne API
* WebSocket via Django Channels
* Celery worker
* Celery Beat
* PostgreSQL
* Redis
* private media storage (shared logical path; mount strategy validated in PR5)

**Cloudflare is not required for V1** and is **out of scope for PR2–PR9**.

Cloudflare may be added later (PR10+) as an optional DNS / edge / cache / protection layer, after the Railway prod-test is validated in the field.

## Architecture retained (Option A only)

Prod-test V1 uses **one Railway Project** with:

| Service | Visibility | Role |
|---|---|---|
| `api-web` | **Public HTTPS** | Django + Daphne + Channels; future static SPA on same origin |
| `celery-worker` | Private | Celery worker |
| `celery-beat` | Private | Celery Beat scheduler |
| `postgres` | Private | Railway PostgreSQL |
| `redis` | Private | Railway Redis |

**Not in V1:**

* separate Railway frontend service
* full Cloudflare in the critical path
* Cloudflare Workers, D1, or Durable Objects

There is no alternative architecture for prod-test V1. See [`railway_architecture.md`](railway_architecture.md) for service roles and dependencies.

## Decisions

1. Single public origin / same-origin architecture.

   The frontend, API and WebSocket routes must be reachable from the same public HTTPS origin.

   Target shape:

   ```txt
   https://<railway-domain>
   /api/* -> Django / Daphne
   /ws/*  -> Django Channels / Daphne
   /*     -> frontend static SPA (future; served from api-web)
   ```

   The frontend uses `baseUrl: ''` (same-origin). No separate API base URL is required in prod-test.

2. HTTPS mandatory via Railway Public Networking for V1.

   The prod-test must run on an HTTPS Railway domain or custom Railway domain.

   Cloudflare is not part of the V1 critical path.

   Future Cloudflare integration must be handled in a separate PR after Railway V1 is validated.

3. PWA cache policy: shell only.

   The PWA may cache the frontend shell and static build assets.

   The following surfaces must remain network-only:

   * `/api/*`
   * `/ws/*`
   * uploads
   * transcription
   * private media
   * operational data

   No runtime cache may be added for API, WebSocket, upload, transcription or media flows.

4. No offline business workflow in prod-test.

   Prod-test V1 does not support offline observation submission.

   No offline queue.

   No background sync.

   If the network is unavailable, the app must fail clearly and avoid pretending that an observation has been submitted.

5. Private media policy.

   Photos are private and may be persisted when linked to an observation.

   Temporary unlinked photos keep their TTL cleanup policy.

   Raw audio is never persisted.

   Audio is only temporarily processed for transcription and then deleted.

   Private media must not be exposed through a public `/media` route.

   **Shared storage requirement:** any service that reads, purges, or processes private media (`api-web`, `celery-worker`) must have access to the same private storage at the same logical path (`HOUSTON_PRIVATE_MEDIA_ROOT`). The exact Railway volume mount or alternative will be validated in **PR5** — this document does not freeze the Railway mount layout.

6. WebSocket reliability is mandatory.

   WebSocket must work on Railway HTTPS/WSS.

   The app must support reconnect behavior.

   A heartbeat / keepalive strategy must be documented or implemented before wider pilot testing.

   After reconnect, operational data must be refetched or invalidated safely.

7. Celery worker and Celery Beat are mandatory in prod-test.

   The prod-test environment must include:

   * `api-web` service
   * `celery-worker` service
   * `celery-beat` service
   * `postgres` service
   * `redis` service

   Celery Beat is not optional in prod-test.

   If Celery worker is down, observation processing and AI signal generation are considered **broken** and **blocking** for prod-test.

8. PostgreSQL is the source of truth.

   PostgreSQL must have a backup strategy before external testers are invited.

   Minimum V1 requirement:

   * daily DB backup
   * documented restore procedure
   * backup verification before wider testing

9. Private media backup is required.

   Private uploaded photos must be backed up separately from PostgreSQL.

   Media restore must be documented.

10. Redis is an operational dependency, not the source of truth.

    Redis is used for cache, throttling, Channels, Celery broker/result backend.

    Redis must **not** be publicly exposed.

    For V1, Redis loss may cause transient operational disruption, but must not be the only copy of business data.

    Redis monitoring is required.

11. Railway variables are the deployment contract.

    All prod-test variables must be explicitly documented in [`.env.prod-test.example`](../../.env.prod-test.example) and [`railway_architecture.md`](railway_architecture.md).

    Required categories:

    * Django security
    * allowed hosts
    * CSRF trusted origins
    * Postgres
    * Redis
    * Celery
    * OpenAI
    * private media
    * auth salts / peppers
    * registration invite codes

12. Cloudflare is future scope (PR10+).

    Cloudflare is **out of scope for V1 and PR2–PR9**.

    Cloudflare may be added later for:

    * custom DNS
    * edge cache
    * WAF / protection
    * asset caching
    * traffic hardening

    It must not block Railway V1. No full Cloudflare proxy, Workers, D1, or Durable Objects in prod-test V1.

## Explicit prohibitions

The following are **forbidden** in prod-test V1:

| Prohibition | Reason |
|---|---|
| `DJANGO_DEBUG=1` | Exposes internals; weakens throttling and cookie security |
| Secrets in `VITE_*` | Frontend build vars are public in the browser bundle |
| Publicly exposed Redis | Operational dependency; not an auth boundary |
| `HOUSTON_AI_OBSERVATION_PROVIDER=fake` | Prod-test must use real AI semantics (`openai`) |
| `HOUSTON_AI_TRANSCRIPTION_PROVIDER=fake` | Same as above |
| Public `/media` route | Private media is served only through authorized API endpoints |
| Offline queue / background sync | No offline business workflow in prod-test |
| Separate Railway frontend service | Breaks same-origin; Option A only |
| Cloudflare in critical path (PR2–PR9) | Railway Public Networking is the V1 HTTPS path |

## Variable classification

See [`railway_architecture.md`](railway_architecture.md) for the full per-service table. Summary:

| Category | Examples | Notes |
|---|---|---|
| Public frontend | none with secrets | Same-origin prod-test uses `baseUrl: ''`; no API secret belongs in `VITE_*` |
| Backend-only | `HOUSTON_PRIVATE_MEDIA_ROOT`, `HOUSTON_LOG_LEVEL` | Set on `api-web`, `celery-worker`, `celery-beat` |
| Secrets (manual) | `DJANGO_SECRET_KEY`, `OPENAI_API_KEY`, auth salts/peppers | Generate before deploy; never commit real values |
| Railway-generated | `POSTGRES_*` connection vars, `REDIS_URL` | Provided by Railway Postgres/Redis plugins; map to Houston env names |
| Manual (operator) | `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `HOUSTON_REGISTRATION_INVITE_CODES` | Set from the public Railway domain and onboarding policy |

## Related documents

* [`railway_architecture.md`](railway_architecture.md) — services, variables, healthcheck, ops
* [`.env.prod-test.example`](../../.env.prod-test.example) — prod-test environment template
