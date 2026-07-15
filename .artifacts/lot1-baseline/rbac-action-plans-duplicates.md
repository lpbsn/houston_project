# RBAC action_plans — matrice doublons (Lot 1, revue statique)

Méthode: grep patterns sur `test_permissions.py`, `test_action_plan_permission_hints_api.py`, et `test_*api*.py`.

## Synthèse par règle (occurrences textuelles)

| Règle métier | Unit permissions | Hints API | API 403 / hints inline | Couches ≥2 |
|--------------|------------------|-----------|------------------------|------------|
| create / catalog | 23 | 2 | 3 | **3** |
| can_use catalog | 12 | 6 | 11 | **3** |
| manage catalog (update/deactivate/activate) | 7 | 6 | 8 | **3** |
| can_mark_done execution | 2 | 4 | 8 | **3** |
| can_validate execution | 6 | 1 | 2 | **3** |
| can_cancel execution | 4 | 1 | 3 | **3** |
| can_execute task | 14 | 0 | 0 | **1** (unit seul) |
| can_schedule | 0 | 1 | 3 | **2** |
| cross_pole / linked plan | 28 | 0 | 11 | **2** |
| visibility / readable | 75 | 0 | 64 | **2** |

## Doublons confirmés (même rôle × même assertion effective × couches multiples)

| Scénario | Unit (`test_permissions.py`) | Hints (`test_action_plan_permission_hints_api.py`) | API 403 (`test_*api*.py`) | Verdict |
|----------|------------------------------|-----------------------------------------------------|---------------------------|---------|
| Owner mark_done + cancel on execution | `test_pilot_manager_can_mark_done_validate_reopen_cancel` | `test_execution_hints_align_with_rbac` (owner can_mark_done, can_cancel) | `test_pilot_assignee_can_mark_done`, 403 paths in `test_action_plan_executions_api.py` | **Triplé** |
| Staff assignee mark_done, no validate | `test_pilot_assignee_can_mark_done` | `test_execution_hints_align_with_rbac` (staff can_mark_done=False for validate) | `test_action_plan_executions_api.py` hints assertions | **Triplé** |
| Owner catalog can_use / can_update | `test_owner_can_manage_catalog_plan`, `test_manager_can_use_catalog_when_pilot_in_scope` | `test_catalog_detail_hints_for_owner` | `test_action_plans_api.py` list permission_hints | **Triplé** sur can_use |
| Staff cannot create catalog | `test_staff_cannot_create_catalog_plan` | — | `test_staff_create_with_schedule_returns_403`, create 403 in `test_action_plans_api.py` | **Doublé** unit+API |
| Staff feed create allowed | `test_staff_feed_create_allowed` | — | mixed submission / feed API | **Doublé** (API couvre HTTP) |
| Cross-pole visibility | `test_contributor_manager_can_see_cross_pole_execution` | — | `test_execution_feed_api.py`, tenant isolation 404 | **Doublé** unit+API (hints absents) |
| Mention readable not visible | `test_mentioned_out_of_scope_staff_is_readable_not_visible` | — | feed/detail API visibility | **Doublé** |

## Non-doublons (couche unique ou complémentaire)

| Zone | Raison de garder |
|------|------------------|
| `can_execute task` (14 tests unit) | Aucun hint/API 403 équivalent — règles fines task-level |
| Hints task_execution (`can_skip`, `can_create_observation`) | État done/pending — pas matrice unit complète |
| Tenant isolation 404 | Contrat HTTP, pas bool permission |

## Hypothèse (non mesurée)

La triplication owner/staff mark_done pourrait être réduite en Lot 4 **sans perte** si les hints API sont générés directement depuis les fonctions permissions déjà testées en unit — **à valider** par revue serializer.
