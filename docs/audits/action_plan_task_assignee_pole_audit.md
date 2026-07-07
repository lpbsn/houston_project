# Action plan task assignee / pole coupling audit

Date: 2026-07-07  
Scope: création tâche (draft assigné↔pôle), validation backend, user search, RBAC tâche ouverte au pôle.

## Files inspected

- Backend: `apps/api/houston/action_plans/services.py`, `permissions.py`, `selectors.py`, `permission_hints.py`
- Establishments: `apps/api/houston/establishments/selectors.py`, `membership_scope.py`, `api/serializers.py`
- Frontend: `action-plan-task-draft-editor.tsx`, `action-plan-task-assignee-sheet.tsx`, `action-plan-form-validation.ts`, `action-plan-create-payload.ts`, `resolve-task-pole-assignee-state.ts`
- Docs: `docs/evolution_action/decisions_plan_action.md` §26.7, §26.8

## Product decisions (locked)

1. Draft sans pôle → assigné choisissable ; filtre par pôle seulement si pôle sélectionné.
2. Submit sans pôle explicite → `business_unit = pilot_business_unit` (sauf dérivation assigné).
3. Assigné 1 pôle → pôle verrouillé ; N pôles → picker restreint obligatoire.
4. Tâche sans `assigned_membership` sur pôle **≠ pilote** → visibilité + exécution pour membres actifs du pôle.
5. Tâche avec assigné → règle existante (staff = assigné plan + scope).
6. Tâche sans assigné sur **pôle pilote** → assignation plan requise (pas de règle ouverte).

## Follow-up (2026-07-07)

| ID | Problem | Resolution |
|----|---------|------------|
| APTA-11 | Pôle invisible après sélection assigné (UI affichait `task.businessUnitId` au lieu de `effectiveBusinessUnitId`) | `PlanningOptionRow` + fallback label dans `resolve-task-pole-assignee-state` |
| APTA-12 | Règle ouverte s'appliquait au pôle pilote | `_is_non_pilot_unassigned_task` dans permissions + exclusion dans feed `Exists` |
| APTA-13 | Changement de pôle effaçait l'assigné Owner/Director (héritage pole-first) ; picker ne montrait qu'un pôle | `shouldClearAssigneeOnPoleChange` + `isAdminAssigneeTask` dans `resolve-task-pole-assignee-state`, utilisé par `handleBusinessUnitChange` |
| APTA-14 | `WheelColumn` déclenchait `onChange` au scroll programmatique à l'ouverture (`value=""` → index 0) | Garde `isSyncingScrollRef` dans `planning-wheel-column.tsx` |
| APTP-01 | Pôle pilote : `value` wheel = `resolved` (fallback) mais stockage = `pilotBusinessUnitId` explicite | `value={pilotBusinessUnitId}` + `displayValue` résolu dans `action-plan-create-page.tsx` |
| APTP-02 | Garde wheel insuffisante (`scroll-smooth` après 1 rAF) | `scrollBehavior: auto` + sync stable (`scrollend` / rAF) dans `planning-wheel-column.tsx` |
| APTP-03 | Pôle tâche : wheel `value=effective` mais `onChange` écrit `businessUnitId` explicite | `value={task.businessUnitId}` + `displayValue` conditionnel dans draft editor |
| APTP-04 | Sans assigné, `businessUnitId` set filtrait `poleOptions` à 1 BU | Branche défaut : toujours `poleOptions: businessUnits` |

## Findings and resolution

| ID | Sev | Problem | Resolution | Tests |
|----|-----|---------|------------|-------|
| APTA-01 | P1 | Assigné bloqué sans pôle (`canPickAssignee = Boolean(task.businessUnitId)`) | Machine à états `resolve-task-pole-assignee-state` + draft editor | `action-plan-task-draft-editor.test.tsx` |
| APTA-02 | P1 | Tâches sans pôle exclues du payload create | Fallback `pilotBusinessUnitId` dans `buildTaskPayloads` | `action-plan-create-payload.test.ts` |
| APTA-03 | P1 | User search sans `business_unit_id` expose tout l'établissement (manager) | Filtre `membership_is_assignable_by_actor` sur scopes acteur | `test_user_search_business_unit_filter.py` |
| APTA-04 | P1 | Search result sans scopes BU pour multi-pôle UI | `business_unit_ids` sur `ScopedUserSearchResult` | serializer + types générés |
| APTA-05 | P1 | §26.8 ne couvrait pas tâche ouverte au pôle | Doc §26.8 complétée | doc |
| APTA-06 | P1 | Staff non assigné plan ne peut pas exécuter tâche ouverte | `is_open_pole_task_for_membership` dans `can_execute_action_plan_task` | `test_permissions.py`, `test_task_services.py` |
| APTA-07 | P2 | Staff pôle ne voit pas exécution avec tâche ouverte | `execution_has_open_pole_task_in_member_scopes` dans visibility | feed + permission tests |
| APTA-08 | P2 | Feed personnel staff ignore tâches ouvertes | `Exists` open-pole dans `action_plan_execution_personal_feed_q` | `test_execution_feed_api.py` |
| APTA-09 | P2 | `business_unit_id` requis sans fallback pilote backend | `_resolve_task_business_unit` + propagation `pilot_business_unit` | `test_execution_services.py`, `test_task_enrichment.py` |
| APTA-10 | P2 | Tests FE verrouillaient pole-first | Réécriture draft editor + helpers | FE tests |
| APTA-13 | P1 | Owner/Director : ouverture picker pôle effaçait assigné et filtrait à 1 pôle | `shouldClearAssigneeOnPoleChange` (jamais clear pour admin) + editor | `resolve-task-pole-assignee-state.test.ts`, `action-plan-task-draft-editor.test.tsx` |
| APTA-14 | P1 | Wheel `onChange` parasite au mount | `isSyncingScrollRef` + sync stable dans `planning-wheel-column.tsx` | `planning-wheel-column.test.tsx` |
| APTP-01 | P1 | Pilote : confusion valeur affichée / stockée | `value` explicite + `displayValue` résolu | `action-plan-create-page.test.tsx` |
| APTP-02 | P1 | Wheel scroll tardif après sync | `scrollBehavior: auto` + `scrollend`/rAF | `planning-wheel-column.test.tsx` |
| APTP-03 | P1 | Tâche : wheel `effective` vs `businessUnitId` | `value` explicite + `displayValue` pilote | `action-plan-task-draft-editor.test.tsx` |
| APTP-04 | P1 | Options tâche filtrées sans assigné | `poleOptions: businessUnits` toujours | `resolve-task-pole-assignee-state.test.ts` |

## Override vs audit APTP-01

`action_plan_task_pole_ux_audit.md` (APTP-01) recommandait de retirer le fallback pilote au draft. Décision produit actuelle **réintroduit** le fallback au submit uniquement ; le draft peut rester sans pôle explicite. Documenté dans §26.7.

## Validation

```bash
make backend-test ARGS="houston/action_plans/tests/test_permissions.py ..."
cd apps/web && npm test -- action-plan-create-page action-plan-task-draft-editor resolve-task-pole-assignee-state planning-wheel-column planning-option-row
make schema && make web-api-generate
```
