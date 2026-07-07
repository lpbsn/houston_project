# Action Plan Task Uncheck — audit & implementation

Date: 2026-07-06  
Scope: décochage d'une tâche `done` → `pending` dans le détail d'exécution  
Mode: implementation complete

## Product mapping

| Règle produit | Implémentation technique |
|---------------|-------------------------|
| Plan modifiable | `execution.status in ACTIVE_EXECUTION_STATUSES` (`in_progress`, `pending_validation`) |
| Plan résolu/terminé | `execution.status == done` → mutation refusée |
| Plan annulé | `execution.status == canceled` → mutation refusée |
| Décochage tâche terminée | `POST .../mark-pending/` si `task.status == done` |
| Permissions | Même RBAC que mark-done : `can_execute_action_plan_task` |
| Progression | `treated_task_count` et `contribution_status` recalculés à la lecture après invalidation |
| Hors scope | `skipped`, `observation_created` — UI distincte, pas de réversion |

## Findings addressed

| ID | Severity | Resolution |
|----|----------|------------|
| AP-UNCHECK-01 | P0 | Service `mark_execution_task_pending` + endpoint `mark-pending` |
| AP-UNCHECK-02 | P1 | Hint `can_unmark_done` backend + `canShowActionPlanTaskUnmarkDone` frontend |
| AP-UNCHECK-03 | P1 | Checkbox cochée cliquable quand `can_unmark_done` |
| AP-UNCHECK-04 | P1 | Tests service, API, selectors, feed, hints, tenant isolation, UI |
| AP-UNCHECK-05 | P2 | Documenté : modifiable = `ACTIVE_EXECUTION_STATUSES` |
| AP-UNCHECK-06 | P2 | `reopen` exécution ne reset pas les tâches — comportement inchangé |

## Changes delivered

| Area | Change |
|------|--------|
| [`services.py`](../../apps/api/houston/action_plans/services.py) | `mark_execution_task_pending` |
| [`permission_hints.py`](../../apps/api/houston/action_plans/permission_hints.py) | `can_unmark_done` |
| [`api/views.py`](../../apps/api/houston/action_plans/api/views.py), [`urls.py`](../../apps/api/houston/action_plans/api/urls.py) | `ActionPlanExecutionTaskMarkPendingView` |
| [`api/serializers.py`](../../apps/api/houston/action_plans/api/serializers.py) | Hint serializer field |
| Frontend | `markActionPlanTaskPending`, hook, checkbox unmark, pole/detail wiring |
| Tests | Backend + frontend ciblés |
| OpenAPI | `make schema && make web-api-generate` |

## Out of scope (unchanged)

- Réversion `skipped` / `observation_created`
- `reopen_action_plan_execution` ne remet pas les tâches en `pending`
- Refonte actions sheet

## Validation

- `docker compose exec api uv run pytest houston/action_plans/tests/test_task_services.py houston/action_plans/tests/test_action_plan_execution_tasks_api.py` (mark-pending cases)
- `cd apps/web && npm run typecheck`
- `cd apps/web && npm test -- action-plan`

## Risks / not verified

- Comportement si toutes les tâches sont décochées alors que l'exécution est en `pending_validation` (attendu : statut exécution inchangé)
- Tests E2E navigateur non exécutés
