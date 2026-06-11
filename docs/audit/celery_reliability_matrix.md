# Celery reliability matrix — Phase M (2026-06-11)

Per-task idempotency and retry policy for Houston Celery jobs. Matches implemented behavior after Phase M.

**Scheduler:** Beat entries in `CELERY_BEAT_SCHEDULE` require a `celery-beat` process (`make up-scheduler`). Lazy read-path fallbacks remain for checklist materialization.

| Task | Idempotent | Safe to double-run | Retry policy | Timeout policy | Failure terminal state | Recovery path | Logging |
|------|------------|-------------------|--------------|----------------|------------------------|---------------|---------|
| `process_observation_task` | partial — pipeline writes are guarded by processing status | yes on `PROCESSED`/`FAILED`; no duplicate signals when status gate holds | Celery `max_retries=3`, `default_retry_delay=30` only when DB status is `RETRYING` after transient AI errors; service sets `RETRYING`/`FAILED` via `_mark_processing_retry_or_failed` (`attempt_count < 3`) | `time_limit` / `soft_time_limit` aligned to `HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS` + buffer | `FAILED` with `last_error_code` when attempts exhausted or terminal pipeline errors | Stuck `PROCESSING` longer than `HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS` → `RETRYING` or `FAILED`; inline on task re-entry + optional `recover_stuck_observation_processing_task` beat sweep | `houston.core.observability` helpers; no raw observation text |
| `recover_stuck_observation_processing_task` | yes | yes — beat overlap safe | explicit no Celery retry (`max_retries=0`) | beat task time limits | n/a (sweeper only) | resets stale `PROCESSING` rows so `process_observation_task` can re-enter | safe processing context fields only |
| `materialize_checklist_assignments_horizon_task` | yes | yes — horizon materialization is upsert-safe | explicit no Celery retry | beat task time limits | n/a — exceptions propagate; next beat run retries operationally | read-path `ensure_visible_executions_materialized` safety net | `build_celery_task_failure_log_context` on failure |
| `purge_chat_messages_task` | yes | yes — batch delete by retention window | explicit no Celery retry | beat task time limits | n/a | next beat run | counts in success log; failure context on error |
| `cleanup_expired_uploads_task` | yes | yes — already-deleted rows skipped | explicit no Celery retry (`max_retries=0`) | beat task time limits | n/a | next beat run | `deleted_count` on success; `build_celery_task_failure_log_context` on failure; no storage paths |

## Enqueue semantics (`submit_observation`)

- `transaction.on_commit` → `process_observation_task.delay(observation_id)`.
- Broker enqueue failure is logged (`observation_processing_enqueue_failed`) and re-raised; observation remains `QUEUED` — ops may re-enqueue manually or wait for a future recovery hook.
- Rollback before commit does not call `.delay()` (tested).

## Celery vs service retries (`process_observation_task`)

- **Service layer:** each pipeline run increments `attempt_count`; transient `ObservationPipelineUnavailableError` / `ObservationPipelineTimeoutError` → `RETRYING` while `attempt_count < 3`, else `FAILED`.
- **Celery layer:** `self.retry()` fires only when the service left status `RETRYING` (transient errors). Terminal errors (`ObservationPipelineInvalidOutputError`, other `ObservationPipelineError`) mark `FAILED` and return without Celery retry.
- `max_retries=3` on the task aligns with operational Celery redelivery, not the service attempt cap.

## Settings reference

| Setting | Purpose |
|---------|---------|
| `HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS` | AI provider timeout |
| `HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS` | Stuck `PROCESSING` recovery threshold (default `2 ×` AI timeout) |
| `HOUSTON_CELERY_OBSERVATION_PIPELINE_*_TIME_LIMIT_SECONDS` | `process_observation_task` limits |
| `HOUSTON_CELERY_BEAT_TASK_*_TIME_LIMIT_SECONDS` | Beat/maintenance task limits |
