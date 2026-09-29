# Scalability PR 1 — baseline before the broker switch

Measured on 2026-09-29 before the RabbitMQ and retry-ownership changes in this delivery.

Repository state at measurement: working tree on the scalability branch, product code not yet switched. Live topology was read from Railway project `graceful-intuition` (`1660997b-4a53-456c-a43d-10952867f530`), environment `production`, without reading variable values.

This note records only the measurements that condition PR 1: current worker concurrency, connection arithmetic for the three pools, the Railway checklist, and the current stacked provider-call count. Dashboard, feed, transcription, and Redis-down gates stay with PR 2 and PR 3.

## Worker concurrency

Live `Celery-worker` deploy `cabc95c1-5d85-4fd9-99c7-1aa74505e704` (2026-09-29T09:42:48Z) logged:

`concurrency: 4 (prefork)`

One replica. `CELERY_WORKER_CONCURRENCY` is set on that service. The numeric value above comes from the worker banner, not from a variable dump.

Initial concurrency written for each of the three pools (`ai_interactive`, `operational`, `ai_background`+`maintenance`) is this same validated value: **4**. It is not a new split of the single worker. Total prefork children therefore go from 4 to 12. `worker_prefetch_multiplier=1` applies only to `ai_interactive`.

## Connection arithmetic

`HOUSTON_DB_CONN_MAX_AGE` is absent from the live API and worker variable names, so the code default **60** applies. `CONN_MAX_AGE=0` and PgBouncer are not decided here. G-conn remains a PR 2 gate.

Current processes, one replica each:

| Process | Postgres connections held up to 60s |
| --- | --- |
| API Daphne | One connection per sync thread that touched the database. No app-level pool cap. Channels runs in this process and does not add a second database process. |
| Celery worker | Up to 4 prefork children. |
| Celery beat | 1 process. The scheduler file is on the beat volume; the process can still open one Django connection. |

Projected after this PR, with `N` API replicas and three pools at concurrency 4:

`N × (concurrent sync DB users on that replica) + 12 worker children + 1 beat`

The worker side grows by 8 connections versus today. `max_connections` on the live Postgres instance was not read. That comparison, and any PgBouncer decision, belongs to G-conn.

Two runtime `iterator()` calls stay in workers and do not block `CONN_MAX_AGE` as it is today: upload cleanup (`apps/api/houston/uploads/services.py`) and gamification rollover (`apps/api/houston/gamification/tasks.py`). They would block a future transaction-pooling PgBouncer. They are unchanged in this PR.

## Railway checklist

Observed on the production environment. No staged changes.

| Check | Observed |
| --- | --- |
| Public HTTP | Only `houston_project`: `https://app.spore-os.com` and `https://spore-os-production.up.railway.app`, port 8080. Workers, beat, Redis, and Postgres have no public HTTP domain. |
| Replicas | 1 for API, Celery-worker, Celery-beat, Redis, and Postgres. Region `europe-west4-drams3a`. |
| Volumes | Redis 500 MB at `/data`. Postgres 500 MB at `/var/lib/postgresql/data`. Beat 5000 MB at `/var/lib/celerybeat`. No RabbitMQ service or volume. |
| TCP proxies | Redis `hayabusa.proxy.rlwy.net:56699` → 6379. Postgres `hayabusa.proxy.rlwy.net:54648` → 5432. The cadrage says permanent public TCP proxies to Postgres or Redis should not stay without an explicit operator reason. This PR does not change them. |
| Broker | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are set on API, worker, and beat. Redis remains the broker until this delivery is deployed. |
| API process | Deploy logs show Daphne listening and `GET /api/v1/health/` 200. The service config field still displays `migrate && sleep 3600`, which does not match the running process or `infra/railway/api-web/railway.toml` (`start-api-web.sh`). Builder is displayed as Railpack while the toml selects the Dockerfile. |
| Worker config file | `/infra/railway/celery-worker/railway.toml`, private network only. |
| Beat | Private, volume mounted, one replica. |

Postgres `max_connections`, backup restore drills, and alert routing are not visible from this inventory.

## Current provider-call stack

Traced from the owning code before this change. A fake provider counts one application call per `propose()` or `classify()`. The OpenAI SDK then multiplies each of those calls by up to `1 + max_retries` HTTP attempts (`max_retries` defaults to 2) before the exception reaches Spore.

Observation, transient timeout or connection error:

- Business ceiling `_MAX_OBSERVATION_PIPELINE_ATTEMPTS = 3`. The third failure marks `failed` and does not call `self.retry()`.
- Celery `max_retries=3` is therefore only partly used: two Celery retries, three application calls.
- SDK multiplier: up to 3 HTTP attempts per application call.
- Maximum HTTP calls on this path: **9**.

A 429 is retried inside the SDK, then leaves `propose()` as an uncaught `RateLimitError`. The pipeline marks a permanent failure after **one** application call (up to 3 HTTP attempts). It does not enter the Celery or business retry loops.

Analytics classification, transient timeout or unavailable on the first provider call (duplicate guard is not reached):

- `finalize_retryable_pattern_classification_error` retries while `request.retries < task.max_retries` (3).
- That is four application calls: the first execution plus three Celery retries.
- SDK multiplier: up to 3 HTTP attempts per call.
- Maximum HTTP calls on this path: **12**.

These counts are the constat. They are not the new budget. After this PR the owner is the existing business ceiling, the SDK `max_retries` is 0, and those two tasks no longer call `self.retry()`. Observation stays at 3 application calls. Analytics keeps the previous gate (`retries < 3`), which is 4 application calls, with delay 30s.
