# Action Plan Execution Feed — deadline sort audit

Date: 2026-07-06  
Scope: feed sorting by `end_at` (intra-section Kanban), cursor pagination, `is_overdue` / `as_of` alignment  
Mode: implementation complete

## Summary

Replaced activity-based feed sort (`-last_activity_at`) with deadline-aware ordering aligned to product rules: overdue first, nearest `end_at`, then items without deadline — within each status section (`pending_validation`, then `in_progress`).

## Changes delivered

| Area | Change |
|------|--------|
| [`feed_cursor.py`](../../apps/api/houston/action_plans/feed_cursor.py) | `Case` expressions, `execution_deadline_bucket` SSoT, multi-key cursor + `as_of` |
| [`selectors.py`](../../apps/api/houston/action_plans/selectors.py) | `apply_action_plan_execution_feed_sorting(as_of)`; `action_plan_execution_overdue` uses shared bucket logic |
| [`execution_feed.py`](../../apps/api/houston/action_plans/execution_feed.py) | Returns `as_of`; encodes cursor with frozen reference time |
| [`api/views.py`](../../apps/api/houston/action_plans/api/views.py) | `is_overdue` computed with page `as_of` |
| Tests | [`test_execution_feed_api.py`](../../apps/api/houston/action_plans/tests/test_execution_feed_api.py) — sort, pagination, invalid cursor, overdue |
| Docs | [`feed_domain.md`](../product/domains/feed_domain.md), [`api_pagination_standard.md`](../engineering/api_pagination_standard.md) |

## Out of scope (unchanged)

- RBAC, visibility, `view_mode`, materialization-on-read
- Frontend Kanban grouping
- DB index on `end_at` (backlog if feed volume grows)

## Validation

- `make backend-lint`
- `make backend-test` (or `pytest houston/action_plans/tests/test_execution_feed_api.py`)

## Risks / not verified

- Pre-deploy opaque cursors invalid after cursor format change (acceptable in dev)
- Index `ap_exec_feed_idx` on `last_activity_at` less aligned with new sort path
