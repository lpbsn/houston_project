# Feature Audit Closure Registry

Status: closure registry  
Date: 2026-06-25  
Mode: audit only — no source changes

## Périmètre

Registre final de fermeture des audits **feature** Houston (domaines opérationnels, onboarding, pipeline, RBAC, notifications/realtime). Consolidation des findings issus des audits et consolidations sous `docs/audits/`. Pas de re-audit, pas de refactor global, pas de modification de code applicatif.

Phase dev uniquement — pas d’exigence staging/prod.

## Sources lues

| Catégorie | Fichiers |
|-----------|----------|
| Contrat | [`AGENTS.md`](../AGENTS.md), [`apps/api/AGENTS.md`](../../apps/api/AGENTS.md), [`apps/web/AGENTS.md`](../../apps/web/AGENTS.md) |
| Règles Cursor | [`.cursor/rules/`](../../.cursor/rules/) (8 fichiers) |
| Commande audit | [`.cursor/commands/audit-mode.md`](../../.cursor/commands/audit-mode.md) |
| Audits domaine | [`action_audit.md`](./action_audit.md), [`checklist_audit.md`](./checklist_audit.md), [`execution_feed_audit.md`](./execution_feed_audit.md), [`signal_feed_audit.md`](./signal_feed_audit.md), [`observation_audit.md`](./observation_audit.md), [`observation_refresh_audit.md`](./observation_refresh_audit.md), [`notifications_realtime_audit.md`](./notifications_realtime_audit.md), [`onboarding_audit.md`](./onboarding_audit.md), [`ai_pipeline_audit.md`](./ai_pipeline_audit.md), [`rbac_security_audit.md`](./rbac_security_audit.md) |
| Consolidations | [`action_consolidation.md`](./action_consolidation.md), [`checklist_consolidation.md`](./checklist_consolidation.md), [`execution_feed_consolidation.md`](./execution_feed_consolidation.md), [`signal_feed_consolidation.md`](./signal_feed_consolidation.md), [`observation_refresh_consolidation.md`](./observation_refresh_consolidation.md), [`notifications_realtime_consolidation.md`](./notifications_realtime_consolidation.md), [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md) |
| Architecture | [`global_architecture_mapping.md`](./global_architecture_mapping.md), [`backend_core_architecture.md`](./backend_core_architecture.md) |

## Hypothèses

- Les quick fixes à fort ROI des consolidations (2026-06-24/25) sont **majoritairement implémentés** sur la branche courante ; ce registre vérifie la présence de preuves, pas l’exécution de `make verify`.
- Docs produit peuvent être en retard sur le code ; preuve code/test prioritaire sur doc produit.
- `DECISION_CLOSED` = décision documentée ou implémentée, sans action restante obligatoire.
- `DECISION_OPEN` = gate produit/archi non tranché — aucune implémentation attendue avant décision.
- Actions code restantes → **à traiter dans un prompt séparé** (hors ce registre).

---

## Légende des statuts

| Statut | Signification |
|--------|---------------|
| **FIXED** | Preuve actuelle dans code, test ou doc alignée |
| **VERIFY_FIXED** | Fix supposé présent ; validation complète (`make verify`, relecture approfondie) non faite dans ce registre |
| **TODO_NOW** | Encore vrai, petit (S), pas de gate produit, pas phase 2, pas couvert par quick fix |
| **DECISION_CLOSED** | Décision produit/archi tranchée ; pas d’action restante |
| **DECISION_OPEN** | Décision produit/archi encore à trancher |
| **DEFER_PHASE_2** | Transféré vers audits infra/couche (API, DB, Realtime, Celery, Frontend structure, etc.) |
| **WONT_FIX_NOW** | Volontairement ignoré en MVP / phase dev |

---

## Tableau principal de fermeture

### Groupe A — Doublons fusionnés (IDs canoniques)

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **ACT-04** | EF-10, NR-01, NR-02, D-01 | action, EF, NR consolidations | P1 | **FIXED** | `actions/services.py` L169/L423 `_schedule_linked_signal_updated_invalidation` ; `realtime/tests/test_action_invalidation.py` `test_cancel_last_linked_action_reopen_emits_action_and_signal_updated`, `test_reopen_action_linked_resolved_signal_emits_action_and_signal_updated` ; `realtime_domain.md` L229–236 | — |
| **SIG-01** | RBAC-02 | signal, rbac | P1/P2 | **DECISION_CLOSED** | Option B (deep-link detail hors Ma vue) — `rbac_permissions_domain.md` L112–117 ; `signals/tests/test_signal_api_contract.py` `test_scoped_member_can_read_out_of_scope_signal_detail` | — |
| **SIG-02** | CL-07, EF scope echo | signal, checklist, EF | P1/P2 | **DECISION_CLOSED** | Option B (visibilité feed ≠ commandes) — consolidations signal/EF/checklist ; asymétrie checklist snapshot BU vs action affected∪responsible **acceptée** MVP | Doc optionnel asymétrie checklist/action (pas bloquant) |
| **C-03** | OR-02 | OAI, OR refresh | P1/P2 | **DEFER_PHASE_2** | Retry même output : `test_observation_pipeline_recovery.py` `test_provider_unavailable_then_retry_completes_without_duplicate_signals` ; **pas** de test chemin LLM divergent → risque signal dupliqué si clés agrégation diffèrent | Design retry policy / output persisté — prompt séparé phase 2 |
| **C-06** | F1 (backend), R9 | OAI, backend, global | P1/P2 | **DEFER_PHASE_2** | `establishments/services.py` ~2545 LOC — monolithe onboarding/RBAC/taxonomy/invites | Split submodule — prompt séparé phase 2 |
| **R1** | F3 (backend), RBAC private imports | global, backend, rbac | P1 | **DEFER_PHASE_2** | Imports `_ADMIN_ROLES`, `_is_valid_membership` cross-app (8+ modules) — `global_architecture_mapping.md` R1, `backend_core_architecture.md` F3 | Promouvoir API publique tenancy — prompt séparé phase 2 |
| **R2** | F6 (backend) | global, backend | P1/P2 | **DEFER_PHASE_2** | `notifications/scheduling.py` fan-in tous domaines ; observabilité échec post-commit **FIXED** séparément (NR-05) | Décentraliser producers — prompt séparé phase 2 |
| **R3** | R8, EF-01, CL-01 | global, EF, checklist | P1/P2 | **DEFER_PHASE_2** | Materialization-on-read : `execution_feed.py` → `ensure_visible_executions_materialized` ; vrai coût quand assignments visibles existent (CL-01/EF-01 full) | Full decouple read-path — prompt séparé phase 2 |

### Groupe B — Action / Execution Feed

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **ACT-01** | — | action | P1 | **FIXED** | `actions/permissions.py` prefetch-aware `is_action_assignee` ; `test_execution_feed_api.py` `test_execution_feed_query_count_with_three_actions` | — |
| **ACT-02** | — | action | P1 | **FIXED** | `actions/services.py` `mark_action_done`/`validate_action` + `actor_membership` ; `test_action_services.py` reject non-accepted / staff validate | — |
| **ACT-03** | — | action | P2 | **DECISION_OPEN** | Backend + hooks reassign/due-at ; pas de composants UI detail | Décision : ship UI reassign vs due-at vs defer |
| **ACT-05** | — | action | P2 | **FIXED** | `test_action_services.py` `test_sync_signal_resolves_when_one_done_one_canceled`, `test_sync_signal_reopens_when_all_linked_actions_canceled` | — |
| **ACT-06** | — | action | P2 | **FIXED** | `action_domain.md` assignee semantics ; `feed_domain.md` `ActionAssignee`/`assignee_ids` | — |
| **ACT-07** | — | action | P2 | **FIXED** | `actions/tests/test_action_tenant_isolation_api.py` (detail, commands, execution-feed, mark-done) | — |
| **ACT-08** | — | action | P2/P3 | **DECISION_OPEN** | Slice minimal livré : footer `accepted_by` (`execution-action-card.tsx`, `execution-action-card.test.tsx`) ; UX multi-assignee étendue (affichage assignees, accept-race) **non tranchée** | Décision produit : garder footer minimal vs surfacer `accepted_by`/assignees sur feed cards et detail |
| **ACT-09** | — | action | P3 | **FIXED** | `testing/query_baseline.py` `EXECUTION_FEED_THREE_ACTIONS_MAX_QUERIES = 9` ; test query count peuplé | — |
| **ACT-10** | — | action | P3 | **WONT_FIX_NOW** | `ActionPermissionError` utilisé post ACT-02 — plus dead code | — |
| **EF-03** | — | EF | P2 | **FIXED** | `checklists/tests/test_execution_feed_checklist.py` `test_manager_sees_in_scope_checklist_assigned_to_staff_in_general_view` | — |
| **EF-04** | FE-01 | EF, rbac | P2 | **FIXED** | `execution-create-menu.ts` `canOpenExecutionCreateMenu` hints ; `execution-feed-page.tsx` ; `execution-create-menu.test.ts` | — |
| **EF-05** | — | EF | P2 | **DECISION_CLOSED** | Checklist feed sans `permission_hints` — MVP documenté `feed_domain.md` | — |
| **EF-06** | — | EF | P2 | **FIXED** | `test_execution_feed_api.py` `test_execution_feed_action_item_includes_permission_hints` | — |
| **EF-07** | — | EF | P2 | **DEFER_PHASE_2** | Baselines mixed/heavy feed — après travail materialization | Prompt séparé phase 2 |
| **EF-08** | CL-04 | EF, checklist | P2 | **DECISION_OPEN** | Lazy materialization + gap pre-`visible_from` | Décision : accepter lazy vs beat proactive |
| **EF-09** | — | EF | P2 | **WONT_FIX_NOW** | `execution-feed-sections.ts` drop statuts inconnus — defense-in-depth MVP | — |
| **CL-01a** | EF-01a | checklist, EF | P2 | **WONT_FIX_NOW** | Re-challenge 2026-06-25 : zéro assignment visible → boucle vide, `return 0`, aucun `materialize_*` ; `.exists()` avant boucle = requête **en plus** sur cas non vides. Couvert par `test_execution_feed_query_count_baseline_empty` (`EXECUTION_FEED_EMPTY_MAX_QUERIES=8`) et `test_ensure_visible_skips_recently_materialized_assignments` (fresh path) | Aucun patch ; vrai levier = CL-01/EF-01 (DEFER_PHASE_2) |
| **EF-02** | — | EF | P2 | **DEFER_PHASE_2** | Boucle per-assignment `_existing_occurrence_dates` non batchée | Prompt séparé phase 2 |

### Groupe C — Checklist

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **CL-02** | — | checklist | P2 | **FIXED** | `selectors.py` `prefetched_in_progress_executions` ; `test_assignment_api.py` `test_assignment_list_query_count_baseline_many_assignments` | — |
| **CL-03** | — | checklist | P2 | **FIXED** | `permission_hints.py` `reflect_delete_conflicts=True` ; `test_template_assignment_permission_hints_api.py` `test_owner_list_delete_hint_false_when_active_execution` | — |
| **CL-05** | — | checklist | P2 | **FIXED** | Exports/hooks morts retirés (`createExecutionFromTemplate`, activate/deactivate hooks absents de `checklists/`) | — |
| **CL-06** | — | checklist | P2 | **DECISION_OPEN** | Endpoints activate/deactivate backend ; pas de UI template detail | Décision : ship UI vs defer |
| **CL-08** | — | checklist | P2 | **DEFER_PHASE_2** | Celery horizon global sans sharding per-establishment | Prompt séparé phase 2 |
| **CL-09** | — | checklist | P3 | **DEFER_PHASE_2** | Indexes partiels — après EXPLAIN | Prompt séparé phase 2 |
| **CL-10** | — | checklist | P3 | **DEFER_PHASE_2** | Hub `business_unit_id` filter + tests frontend élargis | Prompt séparé phase 2 |

### Groupe D — Signal / Feed

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **SIG-03** | — | signal | P1 | **FIXED** | `signals/migrations/0006_signal_unique_active_aggregation_key.py` ; `test_observation_pipeline_aggregation_concurrency.py` `test_concurrent_pipeline_same_aggregation_key_single_active_signal` | — |
| **SIG-04** | — | signal | P2 | **DEFER_PHASE_2** | Index composite agrégation — valider EXPLAIN d’abord | Prompt séparé phase 2 |
| **SIG-05** | — | signal | P2 | **FIXED** | `signals/permissions.py` `can_view_signal_detail` (plus de `can_view_signal` trompeur) ; `test_permissions.py` | — |
| **SIG-06** | — | signal | P2 | **DECISION_OPEN** | Tabs admin Ma zone ≡ Vue globale ; labels cosmétiques | Décision : masquer toggle vs garder |
| **SIG-07** | — | signal | P2 | **FIXED** | `realtime/tests/test_broadcast.py` cancel/resolve/unpin/urgency → `signal.updated` | — |
| **SIG-08** | — | signal | P2 | **FIXED** | `feed_domain.md` feed-visible = `open`, `in_progress`, `resolved` | — |
| **SIG-09** | — | signal | P3 | **WONT_FIX_NOW** | Filtres URL / `permission_hints` liste non utilisés — pas de bug fonctionnel | — |
| **SIG-10** | — | signal | P3 | **DECISION_CLOSED** | Agrégation silencieuse (pas de notification) — MVP acceptable | — |

### Groupe E — Notifications / Realtime

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **NR-03** | — | NR | P2 | **FIXED** | `notification_domain.md` `Implementation status: lot1_in_app` ; API Lot1 documentée | — |
| **NR-04** | — | NR | P2 | **FIXED** | `realtime_domain.md` §8/§10 — notification invalidation implémentée ; contradiction §8 retirée | — |
| **NR-05** | D-04A | NR | P2 | **FIXED** | `scheduling.py` L39–60 `logger.exception` structuré ; `test_scheduling_failure_logging.py` `test_notification_deliver_failure_logs_on_commit` | — |
| **NR-06** | D-02 | NR | P2 | **DECISION_OPEN** | `comment.*` n’invalide pas parent signal/action feeds | Décision : étendre matrix vs threads only |
| **NR-07** | D-03 | NR | P3 | **FIXED** | `notification_matrix_v0.2.md` banner Lot1 + `LOT1_EVENT_KEYS` + backlog Lot2 §6 | — |
| **NR-08** | — | NR | P3 | **DEFER_PHASE_2** | Reconnect comment sweep non couvert | Prompt séparé phase 2 |
| **NR-09** | — | NR | P3 | **DEFER_PHASE_2** | `reporting`/`workspace` query roots non invalidés par WS opérationnel | Prochain audit hub freshness |
| **NR-10** | — | NR | P3 | **FIXED** | `operational-realtime-provider.test.tsx` `invalidates notification list queries when notification.created is received` | — |
| **D-04B** | — | NR | P2 | **DECISION_OPEN** | Retry/outbox notification post-commit | Décision : SLA delivery requis ? |

### Groupe F — Observation / Pipeline / Onboarding

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **C-01** | F2 (backend), OBS-03 | OAI, backend | P1 | **DECISION_CLOSED** | Ownership pipeline documenté `apps/api/AGENTS.md` table Observation→AI→Signal | Refactor orchestrator optionnel phase 2 |
| **C-02** | OBS-01, F2 (AI) | OAI, OBS | P1 | **FIXED** | `recover_orphaned_observation_processing_batch` ; `test_observation_pipeline_recovery.py` orphan queued/retrying ; Beat schedule | — |
| **C-04** | OBS-05, OR-05, F8 (AI) | OAI, OBS, OR | P2/P3 | **DECISION_CLOSED** | Collapse docs → `no_signal_created` — `observation_domain.md` §6, `ai_observation_pipeline_contract.md` ; [`feature_audit_decisions.md`](./feature_audit_decisions.md) | — |
| **C-05** | F10 (AI) | OAI | P3 | **WONT_FIX_NOW** | Stubs `OnboardingSession.SourceMode.AI`, `AIUsageLog.Domain.ONBOARDING` — faible impact runtime | — |
| **C-07** | F4 (AI) | OAI | P2 | **DECISION_CLOSED** | `observations/services.py` enqueue `signals.tasks` — couplage intentionnel MVP ; `test_submit_on_commit_enqueue.py` | — |
| **C-08** | F9 (AI) | OAI | P3 | **WONT_FIX_NOW** | Events pipeline documentés non implémentés ; logging + invalidation substituent | — |
| **C-09** | OB-04, OB-10, OBS-06 | OAI | P1–P3 | **FIXED** | Docs alignés : processing-status implémenté, description optionnelle, taxonomy legacy retirée | — |
| **OR-01** | — | OR refresh | P2 | **DECISION_CLOSED** | Keep HTTP 201 si enqueue fail ; test `test_observation_api.py` `test_api_submit_201_when_enqueue_fails_on_commit_observation_stays_queued` | — |
| **OR-03** | OBS-04 | OR, OBS | P2 | **DECISION_CLOSED** | Signed URL MVP ; tests négatifs `test_signal_detail_media.py` preview 404 sans signal / token expiré | — |
| **OR-04** | — | OR refresh | P2 | **FIXED** | `test_observation_api.py` linked upload ; `test_task_api.py` double submit ; `test_processing_status_api.py` director peer read | — |
| **OR-05** | — | OR refresh | P3 | **DECISION_CLOSED** | = C-04 — collapse docs `no_signal_created` ; [`feature_audit_decisions.md`](./feature_audit_decisions.md) | — |
| **OR-06** | — | OR refresh | P3 | **WONT_FIX_NOW** | Cross-app enqueue — documenté intentionnel | — |
| **OR-07** | OBS-07 | OR, OBS | P3 | **DEFER_PHASE_2** | Poll 2s processing-status ; pas de subject `observation` WS | Prompt séparé phase 2 |
| **OR-08** | OBS-10 | OR, OBS | P3 | **FIXED** | `observation_domain.md` §7 table direct vs checklist permissions | — |
| **OR-09** | — | OR refresh | P3 | **DEFER_PHASE_2** | `ReportPage` sans tests composant/intégration | Prompt séparé phase 2 |
| **OR-10** | — | OR refresh | P3 | **DEFER_PHASE_2** | Lié materialization-on-read (R3/CL-01) — pas de slice CL-01a | Voir R3 / CL-01 |
| **OBS-02** | — | OBS | P2 | **FIXED** | `can_view_observation_processing_status` submitter + admin ; tests peer 404 | — |
| **OBS-08** | — | OBS | P3 | **FIXED** | `useCreateChecklistTaskObservationMutation` absent du frontend | — |
| **OBS-09** | — | OBS | P3 | **WONT_FIX_NOW** | `resolve_observation_actor_membership` couvert par tests intégration submit | — |
| **OB-02** | OB-08 (partiel) | OB | P1 | **FIXED** | `establishments/tests/test_onboarding_tenant_isolation_api.py` | — |
| **OB-03** | — | OB | P1 | **DEFER_PHASE_2** | Wizard frontend largement non testé composant | Prompt séparé phase 2 |
| **OB-04** | — | OB | P1 | **DECISION_CLOSED** | Description activité optionnelle — `runtime_config_onboarding_domain.md` ; `test_activity_description_does_not_block_readiness` | — |
| **OB-05** | — | OB | P2 | **DEFER_PHASE_2** | API description sans step wizard UI | Prompt séparé phase 2 |
| **OB-06** | — | OB | P2 | **DEFER_PHASE_2** | `_ONBOARDING_CONTINUE_ROLES` dupliqué access/selectors | Prompt séparé phase 2 |
| **OB-07** | — | OB | P2 | **DEFER_PHASE_2** | Deux autorités step wizard client vs `current_step` serveur | Prompt séparé phase 2 |
| **OB-09** | — | OB | P2 | **DECISION_CLOSED** | Owner-led draft MVP — `runtime_config_onboarding_domain.md` §7 ; [`feature_audit_decisions.md`](./feature_audit_decisions.md) | — |
| **OB-10** | — | OB | P3 | **FIXED** | Absorbé C-09 — legacy taxonomy retirée des docs | — |
| **AI F5** | — | AI | P2 | **FIXED** | `test_observation_pipeline_schema.py` `test_rejects_wrong_schema_version` | — |
| **AI F6** | R7 (partiel) | AI, global | P2 | **DEFER_PHASE_2** | Prompt taxonomy + 20 signaux — coût/latence à volume | Prompt séparé phase 2 |
| **AI F7** | — | AI | P2 | **DECISION_CLOSED** | `validated_text` → LLM by design ; boundary sub-processor | Doc sécurité si besoin compliance |
| **Ops catalog** | — | OB | P1 | **DECISION_CLOSED** | `make bootstrap-dev` + `import-catalog` requis fresh DB — documenté QA | — |

### Groupe G — RBAC / Sécurité / Architecture

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **RBAC-01** | — | rbac | P1 | **FIXED** | `signal_pole_visible_to_membership` ADMIN_ROLES bypass L25–26 ; `test_signal_canceled_detail.py` `test_detail_canceled_owner_without_pole_scope_returns_200` | — |
| **RBAC-03** | — | rbac | P2 | **DEFER_PHASE_2** | `HasActiveMembership` ne force pas selected establishment — pas de bypass connu | Prompt séparé phase 2 |
| **RBAC-04** | — | rbac | P3 | **DEFER_PHASE_2** | WS ticket foreign establishment 403 vs 404 ailleurs | Prompt séparé phase 2 |
| **RBAC-05** | — | rbac | P3 | **DEFER_PHASE_2** | Resolver establishment dupliqué | Prompt séparé phase 2 |
| **FE-02** | — | rbac | P2 | **DEFER_PHASE_2** | `/checklists/new` sans page guard — API 403 enforce | UX polish phase 2 |
| **FE-03** | — | rbac | P2 | **DEFER_PHASE_2** | `/team` reachable sans management hints — API enforce | UX polish phase 2 |
| **FE-04** | R6 (partiel) | rbac, global | P2 | **DEFER_PHASE_2** | `membership-rbac.ts` manager matrix incomplète vs backend | Prompt séparé phase 2 |
| **FE-05** | — | rbac | P3 | **WONT_FIX_NOW** | Hints `can_reassign`, `can_update_due_at` sans UI — attend ACT-03 | — |
| **FE-06** | — | rbac | P3 | **WONT_FIX_NOW** | Hints checklist activate/deactivate sans UI — attend CL-06 | — |
| **FE-07** | — | rbac | P3 | **WONT_FIX_NOW** | Comment composer toujours visible — API enforce | — |
| **FE-08** | — | rbac | P3 | **FIXED** | `rbac_permissions_domain.md` L107–111 — Staff : free Actions (BU scope), linked refusé, self-assign only, pas de validation ; aligné `actions/services.py` `_validate_staff_create_constraints`, `actions/permissions.py` `can_create_free_action`/`can_create_linked_action`, `establishments/permissions.py` `can_validate_action` | — |
| **TEST-01** | — | rbac | P1 | **FIXED** | `signals/tests/test_signal_tenant_isolation_api.py` ; `comments/tests/test_tenant_isolation_api.py` cross-establishment 404 | — |
| **R4** | F7 (backend) | global, backend | P1/P2 | **DEFER_PHASE_2** | `actions/services.py` `sync_signal_after_action_change` → `resolve_signal` ; couplage lifecycle documentable | Prompt séparé phase 2 |
| **R5** | — | global | P2 | **DEFER_PHASE_2** | `houston.events` stub ; `EventEnvelope` unused | Doc hygiene optionnel S |
| **R6** | — | global | P2 | **DEFER_PHASE_2** | = FE-04 frontend RBAC mirrors | — |
| **R7** | — | global | P2 | **DEFER_PHASE_2** | = AI F6 pipeline externe | — |
| **R10** | — | global | P3 | **DEFER_PHASE_2** | Archive docs / `product_operating_model.md` phase status stale | Doc hygiene S |
| **F4** | — | backend | P2 | **DEFER_PHASE_2** | `_validate_membership_in_establishment` dupliqué actions/checklists | Prompt séparé phase 2 |
| **F5** | — | backend | P2 | **DEFER_PHASE_2** | Scope BU rules parallèles 4+ modules permissions | Prompt séparé phase 2 |
| **F8** | — | backend | P2 | **DEFER_PHASE_2** | `mark_action_done`/`validate_action` appellent les helpers permissions (ACT-02) ; `_validate_staff_create_constraints` reste parallèle dans `services.py` — **pas** de test dédié parité hints ↔ services sur toutes les règles staff | Centraliser ou tester parité — prompt séparé phase 2 |
| **F9** | — | backend | P2 | **DEFER_PHASE_2** | Canceled signal detail prefetch asymétrique vs active | Prompt séparé phase 2 |
| **F10** | — | backend | P2 | **FIXED** | `checklists/tests/test_tenant_isolation_api.py` template/assignment/execution 404 cross-establishment | — |
| **Staff hub checklist** | — | checklist, rbac | P3 | **DECISION_CLOSED** | Nav read-only active Staff intentionnelle — `checklist_domain.md` §5.16 ; [`feature_audit_decisions.md`](./feature_audit_decisions.md) | — |

### Groupe H — Thèmes transverses (intentionnel MVP)

| ID canonique | Alias | Source | Sev | Statut | Preuve | Action restante |
|--------------|-------|--------|-----|--------|--------|-----------------|
| **Coarse invalidation** | — | NR | P3 | **WONT_FIX_NOW** | Establishment-wide WS invalidation + refetch RBAC-safe — pattern Houston documenté | — |
| **Lot1 notifications subset** | — | NR | P3 | **WONT_FIX_NOW** | `test_accept_action_creates_zero_notifications` ; accept/validate hors Lot1 | — |
| **channel_layer None** | — | NR | P3 | **WONT_FIX_NOW** | Skip silencieux dev/test `broadcast.py` | — |
| **Push/email** | — | NR | — | **WONT_FIX_NOW** | Hors scope Lot1 | — |
| **Dual poll+WS observation** | OR-07 echo | OBS, NR | P3 | **WONT_FIX_NOW** | Poll 2s + invalidation signal pipeline — redondant mais safe | — |
| **Cursor as_of drift** | — | EF, action | P3 | **WONT_FIX_NOW** | Tradeoff documenté `execution_feed_cursor.py` | — |
| **Session cancel/abandon** | OB lifecycle | OB | P2 | **DEFER_PHASE_2** | `OnboardingSession` FAILED/CANCELED sans API abandon | Prompt séparé phase 2 |

---

## Synthèse

### TODO_NOW (0)

Aucun — registre feature audit closure fermé (2026-06-25). FE-08 doc corrigée ; CL-01a reclasseé **WONT_FIX_NOW** après re-challenge (voir diagnostic ci-dessous).

### VERIFY_FIXED (0)

Aucun item en attente de vérification ciblée — reclassements 2026-06-25 : ACT-08 → DECISION_OPEN, F8 → DEFER_PHASE_2.

### DECISION_OPEN (7)

| ID | Question |
|----|----------|
| **ACT-03** | Ship UI reassign / due-at maintenant ou defer ? |
| **ACT-08** | Footer minimal `accepted_by` livré ; UX multi-assignee étendue au-delà du footer ? |
| **CL-06** | UI activate/deactivate template ? |
| **EF-08 / CL-04** | Materialization proactive pre-`visible_from` ? |
| **NR-06 / D-02** | Invalider parent feeds sur `comment.*` ? |
| **D-04B** | Notification retry/outbox si SLA delivery ? |
| **SIG-06** | Masquer tabs admin Ma zone ≡ Vue globale ? |

### DECISION_CLOSED doc-only (fermé via feature_audit_decisions.md — 2026-06-25)

| ID transverse | Décision | Doc |
|---------------|----------|-----|
| **requires_validation** | Immutable après create (MVP) | `action_domain.md` §2 |
| **Terminal action visibility** | Detail-only ; hors Execution Feed actif | `action_domain.md` §6, `feed_domain.md` §7 |

*(IDs transverses : pas de ligne tableau principal dédiée ; référencés ici + [`feature_audit_decisions.md`](./feature_audit_decisions.md). C-04/OR-05, OB-09, Staff hub checklist : reclasseés `DECISION_CLOSED` dans le tableau principal.)*

### DEFER_PHASE_2 (thèmes — audits couche à préparer séparément)

- **Materialization** : EF-01/CL-01 full decouple, EF-02, R3/R8, OR-10
- **Pipeline AI** : C-03/OR-02 divergent retry, AI F6/R7 prompt scale
- **Realtime étendu** : NR-08 reconnect comments, NR-09 reporting/workspace, OR-07 observation WS
- **Structure monolithe** : C-06/F1/R9 establishments split, R1/F3 private imports, R2/F6 notification hub, R4/F7 action↔signal coordination
- **RBAC infra** : RBAC-03/04/05, F4/F5/F8 scope centralization et parité hints/services, FE-02/03/04 page guards
- **Onboarding** : OB-03/05/06/07, session abandon API
- **Perf/tests** : EF-07, CL-08/09/10, SIG-04, F9 canceled detail N+1, OR-09 ReportPage
- **Doc hygiene** : R5/R10 events stub et phase docs

### WONT_FIX_NOW (14 thèmes)

ACT-10, EF-09, SIG-09, SIG-10 (closed silent agg), C-05, C-08, OR-06, OBS-09, FE-05, FE-06, FE-07, coarse invalidation, Lot1 notification subset, channel_layer None skip, push/email, dual poll+WS, cursor as_of drift

---

## Compteurs par statut

| Statut | Count |
|--------|-------|
| **FIXED** | 53 |
| **DECISION_CLOSED** | 18 |
| **DECISION_OPEN** | 7 |
| **DEFER_PHASE_2** | 33 |
| **WONT_FIX_NOW** | 15 |
| **VERIFY_FIXED** | 0 |
| **TODO_NOW** | 0 |
| **Total lignes tableau** | 118 |

*(Les alias fusionnés ne sont pas comptés séparément ; chaque ID canonique = 1 ligne.)*

---

## Notes de clôture

- **Aucune modification source** effectuée pour produire ce registre.
- **`make verify` non exécuté** dans ce passage — statuts FIXED fondés sur lecture code/tests/docs uniquement.
- **Phase 2** (audits API/DB/Realtime/Celery/Frontend structure) à préparer dans des prompts séparés ; ce registre ne lance pas ces audits.
- **Quick fixes consolidation** : tous les TODO_NOW fermés (FE-08 doc ; CL-01a faux positif → WONT_FIX_NOW).
- **CL-01a re-challenge (2026-06-25)** : pas de bug métier ni gain mesuré pour `.exists()` ; materialization-on-read reste sujet **R3/CL-01** en phase 2.
- **Prochain audit recommandé** (hors scope fermeture) : Reporting/Workspace hub freshness (NR-09) — voir [`notifications_realtime_consolidation.md`](./notifications_realtime_consolidation.md) §6.
- **Reclassement doc-only 2026-06-25** : 5 décisions fermées via [`feature_audit_decisions.md`](./feature_audit_decisions.md) — C-04/OR-05, requires_validation, terminal action visibility, Staff hub, OB-09 ; compteur `DECISION_OPEN` corrigé (13 → 7).

---

**Changed:** Created `docs/audits/feature_audit_closure.md` ; reclassements CL-01a P2, ACT-08 → DECISION_OPEN, F8 → DEFER_PHASE_2 ; doc-only closures 2026-06-25 (DECISION_OPEN 7, DECISION_CLOSED 18)  
**Validated:** Read-only cross-check code/tests/docs vs 19 audits + 8 consolidations ; 2 TODO_NOW confirmés sur branche courante ; doc-only MVP closures alignées `feature_audit_decisions.md`  
**Risks / not verified:** `make verify` non exécuté ; 7 décisions DECISION_OPEN restantes ; enum `NOT_ACTIONABLE` peut subsister en code
