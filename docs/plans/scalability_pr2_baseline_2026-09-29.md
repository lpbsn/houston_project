# Scalability PR 2 — G-conn and G-transcription

Recorded on 2026-09-29 before `CONN_MAX_AGE=0` and before any transcription isolation. These gates decide PgBouncer and a separate transcription runtime. They do not decide `CONN_MAX_AGE`.

Repository state: PR 1 durable dispatch and the three worker pools are already in the tree. Live topology remains the one recorded in [`scalability_pr1_baseline_2026-09-29.md`](scalability_pr1_baseline_2026-09-29.md): one API replica, worker concurrency 2 + 1 + 1, one beat. `max_connections` on the live Postgres instance is still not readable from this environment.

## G-conn

`CONN_MAX_AGE=0` closes the Django connection at the end of the request or task. Idle connections are not retained. What can be stated from the repo and the PR 1 topology:

| Process | In-flight connections |
| --- | --- |
| One API replica | One connection per in-flight sync request that touches the database. Django 5.2 wraps each ASGI request in `ThreadSensitiveContext`, so those requests are not serialized onto one connection. There is no measured cap on concurrent API requests. |
| Three worker pools | 4 while tasks run (concurrency 2 + 1 + 1). |
| Celery beat | 1 while the scheduler touches the database. |

`max_connections` on the live Postgres instance was not read. No API concurrency figure was measured. This note therefore does not claim that a numeric budget is under the server limit. The gate adds PgBouncer only when that comparison shows the projected peak exceeds Postgres connections with margin. That exceedance is not shown.

The two runtime `iterator()` calls in upload cleanup and gamification rollover stay incompatible with transaction pooling. They are not changed.

Decision: no PgBouncer. No `DATABASE_POOLED` / `DATABASE_UNPOOLED` split. API, workers, and beat use `HOUSTON_DB_CONN_MAX_AGE=0`.

## G-transcription

`TranscriptionCreateView.post` calls `transcribe_audio_file` on the request thread and deletes the temp file in `finally`. Audio is not persisted. The OpenAI client uses `HOUSTON_AI_TRANSCRIPTION_TIMEOUT_SECONDS` (default 10) and `max_retries=0`.

A provider call therefore holds that request's sync thread until it returns or the 10s timeout fires. It does not hold the ASGI process: other requests keep their own threads. The timeout path's duration ceiling is 10s for one thread. There is one API replica and no real concurrent user load that would fill those threads.

Decision: no isolated transcription runtime. No temporary audio storage, no S3 audio, and no RabbitMQ audio message.
