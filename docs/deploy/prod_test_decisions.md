# Prod-test V1 Decisions

## Hosting decision

Prod-test V1 runs on Railway.

Railway hosts the runtime services:

* Django / Daphne API
* WebSocket via Django Channels
* Celery worker
* Celery Beat
* PostgreSQL
* Redis
* private media storage strategy

Cloudflare is not required for V1.

Cloudflare may be added later as a DNS / edge / cache / protection layer, after the Railway prod-test is validated.

## Decisions

1. Single public origin / same-origin architecture.

   The frontend, API and WebSocket routes must be reachable from the same public HTTPS origin.

   Target shape:

   ```txt
   https://<railway-domain>
   /api/* -> Django / Daphne
   /ws/*  -> Django Channels / Daphne
   /*     -> frontend static SPA
   ```

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

6. WebSocket reliability is mandatory.

   WebSocket must work on Railway HTTPS/WSS.

   The app must support reconnect behavior.

   A heartbeat / keepalive strategy must be documented or implemented before wider pilot testing.

   After reconnect, operational data must be refetched or invalidated safely.

7. Celery worker and Celery Beat are mandatory in prod-test.

   The prod-test environment must include:

   * API web service
   * Celery worker service
   * Celery Beat service
   * Postgres service
   * Redis service

   Celery Beat is not optional in prod-test.

   If Celery worker is down, observation processing and AI signal generation are considered broken.

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

Redis must not be publicly exposed unless explicitly required.

For V1, Redis loss may cause transient operational disruption, but must not be the only copy of business data.

Redis monitoring is required.

11. Railway variables are the deployment contract.

All prod-test variables must be explicitly documented.

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

12. Cloudflare is future scope.

Cloudflare may be added later for:

* custom DNS
* edge cache
* WAF / protection
* asset caching
* traffic hardening

It must not block Railway V1.
