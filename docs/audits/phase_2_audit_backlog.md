# Phase 2 Audit Backlog

Status: backlog d’audits infra/couche  
Date: 2026-06-25  
Mode: audit only — aucune modification source, aucun plan d’implémentation

## Périmètre

Ce document **prépare les audits phase 2** (API, DB, Realtime, Celery, cache frontend, structure UI, PWA, DevEx). Ce n’est **pas** un backlog de développement.

**Contexte feature audits :** fermés — [`feature_audit_closure.md`](./feature_audit_closure.md) indique `TODO_NOW = 0`.

**Inclus :**

- Items `DEFER_PHASE_2` du registre de clôture (alias fusionnés ; compteur aligné sur le registre courant : **33 thèmes canoniques**)
- Décisions `DECISION_OPEN` post-phase 2 — section séparée, sans transformation en corrections
- Signaux transverses cités dans [`global_architecture_mapping.md`](./global_architecture_mapping.md) ou [`backend_core_architecture.md`](./backend_core_architecture.md) — à confirmer par audit domaine

**Exclus (ne pas rouvrir) :**

- `FIXED`, `WONT_FIX_NOW`, `DECISION_CLOSED`
- Décisions MVP doc-only fermées 2026-06-25 : C-04/OR-05, requires_validation, terminal action visibility, Staff hub checklist, OB-09
- `CL-01a` / `EF-01a` — reclasseé `WONT_FIX_NOW` ; contexte uniquement pour R3

## Sources lues

| Catégorie | Fichiers |
|-----------|----------|
| Contrat | [`AGENTS.md`](../AGENTS.md), [`apps/api/AGENTS.md`](../../apps/api/AGENTS.md), [`apps/web/AGENTS.md`](../../apps/web/AGENTS.md) |
| Règles Cursor | [`.cursor/rules/`](../../.cursor/rules/) |
| Clôture / décisions | [`feature_audit_closure.md`](./feature_audit_closure.md), [`feature_audit_decisions.md`](./feature_audit_decisions.md) |
| Architecture | [`global_architecture_mapping.md`](./global_architecture_mapping.md), [`backend_core_architecture.md`](./backend_core_architecture.md) |
| Consolidations | [`action_consolidation.md`](./action_consolidation.md), [`checklist_consolidation.md`](./checklist_consolidation.md), [`execution_feed_consolidation.md`](./execution_feed_consolidation.md), [`signal_feed_consolidation.md`](./signal_feed_consolidation.md), [`observation_refresh_consolidation.md`](./observation_refresh_consolidation.md), [`notifications_realtime_consolidation.md`](./notifications_realtime_consolidation.md), [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md) |

## Synthèse

| Domaine d’audit | Items DEFER (domaine principal) | P1 | P2 | P3 |
|-----------------|--------------------------------|----|----|-----|
| API / OpenAPI | 10 | 2 | 7 | 1 |
| Database / ORM | 3 | 0 | 2 | 1 |
| Realtime / Event-driven | 6 | 2 | 2 | 2 |
| Celery / Async | 4 | 1 | 3 | 0 |
| TanStack Query / Cache | 1 | 0 | 0 | 1 |
| Frontend Architecture | 8 | 1 | 5 | 2 |
| PWA / Mobile-first | 0 | — | — | — |
| CI / DevEx / Docs | 1 | 0 | 0 | 1 |
| **Total thèmes canoniques** | **33** | **5** | **17** | **11** |

*Un thème = une entrée (alias fusionnés). Domaines secondaires portés dans chaque fiche. PWA / Mobile-first : relecture transversale §7.*

**Décisions post-phase 2 ouvertes :** 7 (section dédiée, hors compteur DEFER).

---

## Ordre recommandé d’exécution des audits phase 2

1. **API / OpenAPI** — surface tenancy/RBAC, contrats permission, monolithe establishments
2. **Database / ORM** — indexes, prefetch, coût requêtes agrégation
3. **Realtime / Event-driven** — hub notifications, couplage action↔signal, materialization-on-read
4. **Celery / Async** — retry pipeline, horizon checklist, batching materialization
5. **TanStack Query / Cache** — matrice invalidation WS ↔ query roots
6. **Frontend Architecture** — guards, mirrors RBAC, onboarding wizard, couverture tests UI
7. **PWA / Mobile-first** — relecture transversale poll/reconnect/états mobiles sur items 3–6
8. **CI / DevEx / Docs** — baselines query, docs phase, import-graph

---

## 1. API / OpenAPI

**Note — backend boundaries :** Plusieurs thèmes de cette section (tenancy, classes permission DRF, monolithe `establishments`, parité hints/services) recoupent les frontières backend de [`backend_core_architecture.md`](./backend_core_architecture.md). Ils sont audités ici sous l’angle contrat HTTP/OpenAPI et surface API — **sans** phase séparée « Backend Architecture ».

### R1 / F3 — Imports privés cross-app tenancy

- **IDs :** R1, F3 (backend), RBAC private imports
- **Priorité :** P1
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** CI / DevEx / Docs (`signals/tests/test_import_graph.py` comme gate potentielle)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe A ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R1 ; [`backend_core_architecture.md`](./backend_core_architecture.md) F3
- **Pourquoi pas maintenant :** refactor de surface publique tenancy — taille M, ripple 8+ modules ; aucun bypass sécurité connu au registre feature
- **Questions précises à auditer :**
  - Quels symboles `_`-prefixed sont importés cross-app et par quels modules ?
  - Existe-t-il une surface publique documentée dans `establishments/` pour membership validity et rôles admin ?
  - Un nouvel endpoint domaine peut-il contourner le contrat tenancy en copiant un import privé ?
- **Risques à vérifier :** drift RBAC silencieux ; refactor establishments casse N apps sans signal test
- **Fichiers probables à inspecter :** `apps/api/houston/establishments/permissions.py`, `role_constants.py`, `access.py` ; `signals/permissions.py`, `actions/permissions.py`, `checklists/permissions.py`, `chat/permissions.py`, `notifications/permissions.py`, `realtime/permissions.py`
- **Tests existants à inspecter / zones de test à vérifier :** `signals/tests/test_import_graph.py` ; `establishments/tests/test_permissions.py` ; permissions tests par domaine

---

### C-06 / F1 / R9 — Monolithe `establishments/services.py`

- **IDs :** C-06, F1 (backend), R9 (global)
- **Priorité :** P1/P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** Celery / Async (onboarding activation enqueue)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe A ; [`backend_core_architecture.md`](./backend_core_architecture.md) F1 ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md)
- **Pourquoi pas maintenant :** ~2545 LOC, taille L ; tests establishments existants couvrent le comportement MVP
- **Questions précises à auditer :**
  - Quelles responsabilités cohabitent (onboarding FSM, invites, membership CRUD, runtime taxonomy) ?
  - Quels endpoints API dépendent de quelles fonctions du monolithe ?
  - Où les transactions `atomic` + `on_commit` traversent-elles plusieurs sous-domaines ?
- **Risques à vérifier :** conflits merge ; régression onboarding/RBAC lors de toute évolution locale
- **Fichiers probables à inspecter :** `apps/api/houston/establishments/services.py`, `api/views.py`, `api/serializers.py`, `selectors.py`
- **Tests existants à inspecter / zones de test à vérifier :** `establishments/tests/test_onboarding_tenant_isolation_api.py` ; `establishments/tests/test_permissions.py` ; tests onboarding/proposal/invite

---

### RBAC-03 — `HasActiveMembership` vs establishment sélectionné

- **IDs :** RBAC-03
- **Priorité :** P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** —
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`rbac_security_audit.md`](./rbac_security_audit.md)
- **Pourquoi pas maintenant :** pas de bypass connu ; renforcement DRF = changement transversal M
- **Questions précises à auditer :**
  - Quels endpoints s’appuient sur `HasActiveMembership` sans resolver establishment ?
  - Un membership actif hors establishment courant peut-il lire/écrire via un nouvel endpoint mal câblé ?
  - Quelle est la différence sémantique avec les mixins establishment-scoped existants ?
- **Risques à vérifier :** fuite cross-establishment sur futurs endpoints ; incohérence avec bootstrap `selected_establishment`
- **Fichiers probables à inspecter :** `establishments/permissions.py`, `api/views.py` (mixins), `accounts/api/views.py`
- **Tests existants à inspecter / zones de test à vérifier :** `establishments/tests/test_permissions.py` ; tests tenant isolation API (`actions`, `signals`, `observations`, `checklists`)

---

### RBAC-04 — WS ticket : 403 vs 404 établissement étranger

- **IDs :** RBAC-04
- **Priorité :** P3
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** Realtime / Event-driven
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`rbac_security_audit.md`](./rbac_security_audit.md)
- **Pourquoi pas maintenant :** enforcement OK ; polish sémantique S, pas de faille feature audit
- **Questions précises à auditer :**
  - Quel code HTTP le ticket WS retourne-t-il pour foreign establishment vs REST detail ?
  - La divergence est-elle documentée dans `realtime_domain.md` ?
  - Les clients frontend gèrent-ils 403 et 404 de façon équivalente ?
- **Risques à vérifier :** fuite d’existence ressource ; UX debug confuse
- **Fichiers probables à inspecter :** `realtime/access.py`, `realtime/api/views.py`, `realtime/permissions.py`
- **Tests existants à inspecter / zones de test à vérifier :** `realtime/tests/` ; comparaison avec patterns 404 cross-establishment dans `signals/tests/test_signal_tenant_isolation_api.py`

---

### RBAC-05 — Resolver establishment dupliqué

- **IDs :** RBAC-05
- **Priorité :** P3
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** —
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`rbac_security_audit.md`](./rbac_security_audit.md)
- **Pourquoi pas maintenant :** enforcement cohérent aujourd’hui ; déduplication = maintenance S
- **Questions précises à auditer :**
  - Combien de variantes du resolver actor establishment existent ?
  - Les querysets et exceptions diffèrent-ils entre copies ?
- **Risques à vérifier :** drift maintenance ; comportement divergent sur edge membership status
- **Fichiers probables à inspecter :** `establishments/access.py`, `establishments/permissions.py`, `comments/api/views.py`, `checklists/api/views.py`
- **Tests existants à inspecter / zones de test à vérifier :** `establishments/tests/test_permissions.py` ; tests API cross-establishment

---

### F4 — Validation membership-in-establishment dupliquée

- **IDs :** F4
- **Priorité :** P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** —
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`backend_core_architecture.md`](./backend_core_architecture.md) F4
- **Pourquoi pas maintenant :** logique identique, exceptions domaine différentes ; pas de bug signalé
- **Questions précises à auditer :**
  - Les deux copies de `_validate_membership_in_establishment` sont-elles encore byte-identiques sur la requête ?
  - Un troisième domaine a-t-il copié le pattern ?
- **Risques à vérifier :** fix appliqué dans un domaine seulement ; optimisation query manquée
- **Fichiers probables à inspecter :** `actions/services.py` (~L40), `checklists/services.py` (~L130)
- **Tests existants à inspecter / zones de test à vérifier :** `actions/tests/test_action_services.py` ; `checklists/tests/test_assignment_services.py`

---

### F5 — Règles scope BU parallèles (permissions)

- **IDs :** F5
- **Priorité :** P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** Database / ORM (querysets scope)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`backend_core_architecture.md`](./backend_core_architecture.md) F5
- **Pourquoi pas maintenant :** centralisation M ; tests par domaine couvrent les cas connus
- **Questions précises à auditer :**
  - Les 4+ implémentations de « membership couvre BU » divergent-elles sur ADMIN vs MANAGER vs STAFF ?
  - Feed visibility vs command permission utilisent-elles la même primitive ?
- **Risques à vérifier :** faille scope lecture vs écriture ; manager voit/mute hors périmètre
- **Fichiers probables à inspecter :** `establishments/membership_scope.py`, `signals/permissions.py`, `actions/permissions.py`, `checklists/permissions.py`
- **Tests existants à inspecter / zones de test à vérifier :** `establishments/tests/test_membership_scope_coverage.py` ; `signals/tests/test_permissions.py` ; `actions/tests/test_action_permissions.py` ; `checklists/tests/test_permissions.py`

---

### F8 — Parité hints permissions ↔ règles services (actions)

- **IDs :** F8
- **Priorité :** P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** Frontend Architecture (hints UX)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`backend_core_architecture.md`](./backend_core_architecture.md) F8
- **Pourquoi pas maintenant :** ACT-02 a aligné mark-done/validate ; `_validate_staff_create_constraints` reste parallèle ; pas de test parité exhaustive
- **Questions précises à auditer :**
  - Quelles règles staff existent uniquement dans `services.py` vs `permissions.py` ?
  - Les serializers `permission_hints` reflètent-ils toutes les gardes write ?
- **Risques à vérifier :** hint true + API 403 ; hint false + action autorisée
- **Fichiers probables à inspecter :** `actions/services.py`, `actions/permissions.py`, `actions/api/serializers.py`
- **Tests existants à inspecter / zones de test à vérifier :** `actions/tests/test_action_permissions.py` ; `actions/tests/test_action_services.py` ; `test_execution_feed_api.py` (permission_hints)

---

### Session cancel / abandon — API onboarding absente

- **IDs :** Session cancel/abandon (OB lifecycle)
- **Priorité :** P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** Frontend Architecture
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe H ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md)
- **Pourquoi pas maintenant :** pas d’UX abandon produit ; états FAILED/CANCELED existent en modèle
- **Questions précises à auditer :**
  - Quels transitions `OnboardingSession` sont possibles sans endpoint dédié ?
  - Des sessions DRAFT orphelines s’accumulent-elles en dev ?
  - L’absence d’API bloque-t-elle un second client ou un flow mobile ?
- **Risques à vérifier :** hygiène données ; confusion état session vs UI
- **Fichiers probables à inspecter :** `establishments/models.py`, `establishments/services.py`, `establishments/api/views.py`
- **Tests existants à inspecter / zones de test à vérifier :** tests onboarding session lifecycle ; `establishments/tests/test_onboarding_tenant_isolation_api.py`

---

### OB-05 — API description activité sans step wizard

- **IDs :** OB-05
- **Priorité :** P2
- **Domaine principal :** API / OpenAPI
- **Domaines secondaires :** Frontend Architecture
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md)
- **Pourquoi pas maintenant :** description optionnelle MVP (OB-04 fermé doc-only) ; endpoint + hook existent, UI absente
- **Questions précises à auditer :**
  - Le contrat OpenAPI `PATCH .../description/` est-il aligné avec `runtime_config_onboarding_domain.md` ?
  - Le hook `useSubmitActivityDescription` est-il mort ou appelable hors wizard ?
- **Risques à vérifier :** drift contrat/doc ; contexte AI pipeline sous-alimenté si description jamais saisie
- **Fichiers probables à inspecter :** `establishments/api/views.py`, `establishments/api/serializers.py` ; `apps/web/src/features/onboarding/hooks.ts`
- **Tests existants à inspecter / zones de test à vérifier :** `test_description_patch_accepts_valid_description` ; `test_activity_description_does_not_block_readiness`

---

## 2. Database / ORM

### SIG-04 — Index composite lookup agrégation

- **IDs :** SIG-04
- **Priorité :** P2
- **Domaine principal :** Database / ORM
- **Domaines secondaires :** Celery / Async (pipeline write path)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe D ; [`signal_feed_consolidation.md`](./signal_feed_consolidation.md)
- **Pourquoi pas maintenant :** index prématuré sans `EXPLAIN` à volume pilote ; unique constraint aggregation déjà FIXED (SIG-03)
- **Questions précises à auditer :**
  - Quel plan de requête pour `find_active_signal_for_aggregation` à N signaux actifs ?
  - Un index composite ou partiel apporte-t-il un gain mesurable vs index existants ?
- **Risques à vérifier :** latence pipeline ; contention sur hot establishment
- **Fichiers probables à inspecter :** `signals/models.py`, `signals/services.py`, `signals/migrations/`
- **Tests existants à inspecter / zones de test à vérifier :** `test_observation_pipeline_aggregation_concurrency.py` ; `signals/tests/test_signal_lifecycle_services.py`

---

### CL-09 — Indexes partiels checklist

- **IDs :** CL-09
- **Priorité :** P3
- **Domaine principal :** Database / ORM
- **Domaines secondaires :** —
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe C ; [`checklist_consolidation.md`](./checklist_consolidation.md)
- **Pourquoi pas maintenant :** décision index après `EXPLAIN` ; volume dev faible
- **Questions précises à auditer :**
  - Quelles requêtes assignment/execution filtrent `checklist_template_id` + status ?
  - Les indexes actuels couvrent-ils les chemins materialization et hub list ?
- **Risques à vérifier :** seq scan sur bibliothèque template à scale
- **Fichiers probables à inspecter :** `checklists/models.py`, `checklists/selectors.py`, `checklists/migrations/`
- **Tests existants à inspecter / zones de test à vérifier :** `checklists/tests/test_assignment_api.py` ; `test_materialization_services.py`

---

### F9 — Prefetch asymétrique signal detail canceled

- **IDs :** F9
- **Priorité :** P2
- **Domaine principal :** Database / ORM
- **Domaines secondaires :** API / OpenAPI (detail serializer)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`backend_core_architecture.md`](./backend_core_architecture.md) F9
- **Pourquoi pas maintenant :** volume canceled faible en dev ; chemin actif déjà prefetché
- **Questions précises à auditer :**
  - Combien de requêtes SQL pour `get_signal_for_detail` branche canceled vs active ?
  - `serialize_signal_detail` déclenche-t-il des queries observation links ?
- **Risques à vérifier :** N+1 sur review manager signaux archivés
- **Fichiers probables à inspecter :** `signals/selectors.py` (~L142–163), `signals/api/serializers.py`
- **Tests existants à inspecter / zones de test à vérifier :** `signals/tests/test_signal_canceled_detail.py` ; query-count patterns dans tests signal API

---

## 3. Realtime / Event-driven

### R2 / F6 — Hub notifications `scheduling.py`

- **IDs :** R2, F6 (backend)
- **Priorité :** P1/P2
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** API / OpenAPI (after-commit contract)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe A ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R2 ; [`backend_core_architecture.md`](./backend_core_architecture.md) F6
- **Pourquoi pas maintenant :** fichier 526 LOC fan-in ; observabilité échec post-commit FIXED (NR-05) ; décentralisation = L
- **Questions précises à auditer :**
  - Chaque `event_key` de `notification_matrix_v0.2.md` a-t-il un producteur traçable dans `scheduling.py` ?
  - Quels domaines importent directement des modèles étrangers dans ce hub ?
  - Les échecs post-commit sont-ils suffisamment structurés pour diagnostiquer un producteur manquant ?
- **Risques à vérifier :** notification oubliée sur nouveau lifecycle ; merge conflicts ; import cycle
- **Fichiers probables à inspecter :** `notifications/scheduling.py`, `notifications/services.py`, `notifications/constants.py`
- **Tests existants à inspecter / zones de test à vérifier :** `notifications/tests/` ; `test_scheduling_failure_logging.py` ; producer tests par domaine

---

### R4 / F7 — Couplage lifecycle action → signal resolve

- **IDs :** R4, F7 (backend)
- **Priorité :** P1/P2
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** API / OpenAPI (règle produit implicite)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R4 ; [`backend_core_architecture.md`](./backend_core_architecture.md) F7
- **Pourquoi pas maintenant :** couplage intentionnel MVP ; lazy import masque la dépendance ; ACT-04 FIXED séparément pour invalidation
- **Questions précises à auditer :**
  - Quels chemins `sync_signal_after_action_change` appellent `resolve_signal` / reopen ?
  - Quels événements WS/notifications suivent chaque branche ?
  - La règle « all actions terminal → signal resolve » est-elle documentée dans `action_domain.md` / `signal_domain.md` ?
- **Risques à vérifier :** évolution lifecycle indépendante impossible ; ordering side-effects
- **Fichiers probables à inspecter :** `actions/services.py`, `signals/services.py`, `realtime/broadcast.py`
- **Tests existants à inspecter / zones de test à vérifier :** `actions/tests/test_action_services.py` ; `realtime/tests/test_action_invalidation.py`

---

### R3 / R8 / EF-01 / CL-01 / OR-10 — Materialization-on-read (execution feed)

- **IDs :** R3, R8 (global), EF-01, CL-01, OR-10
- **Priorité :** P1/P2
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** Celery / Async, Database / ORM
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupes A, B, F ; [`execution_feed_consolidation.md`](./execution_feed_consolidation.md) ; [`checklist_consolidation.md`](./checklist_consolidation.md)
- **Pourquoi pas maintenant :** acceptable à l’échelle dev ; decouple read-path = M–L ; CL-01a WONT_FIX_NOW
- **Questions précises à auditer :**
  - Quel coût mesuré de `ensure_visible_executions_materialized` sur feed GET avec assignments visibles ?
  - Read-path déclenche-t-il des writes même quand beat horizon a déjà matérialisé ?
  - Quelle stratégie beat/Celery existe vs materialization synchrone ?
- **Risques à vérifier :** latence feed ; lock contention ; amplification lecture→écriture
- **Fichiers probables à inspecter :** `actions/execution_feed.py`, `checklists/materialization.py`, `checklists/tasks.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_execution_feed_query_count_baseline_empty` ; `test_ensure_visible_skips_recently_materialized_assignments` ; `checklists/tests/test_execution_feed_checklist.py`

---

### R5 — Stub `houston.events` / `EventEnvelope` non utilisé

- **IDs :** R5
- **Priorité :** P2
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** CI / DevEx / Docs
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R5
- **Pourquoi pas maintenant :** doc hygiene S ; side-effects ad-hoc fonctionnent via `on_commit`
- **Questions précises à auditer :**
  - `houston.events` dans `INSTALLED_APPS` a-t-il un rôle runtime ?
  - `EventEnvelope` est-il référencé hors tests ?
  - `event_catalogue_v0.1.md` reflète-t-il l’implémentation actuelle ?
- **Risques à vérifier :** nouveaux contributeurs construisent sur mauvaise abstraction
- **Fichiers probables à inspecter :** `houston/events/apps.py`, `core/events.py`, `docs/product/event_catalogue_v0.1.md`, `config/settings.py`
- **Tests existants à inspecter / zones de test à vérifier :** tests `core/events.py` s’il existent ; aucun test prod path attendu

---

### NR-08 — Reconnect WS : sweep commentaires

- **IDs :** NR-08
- **Priorité :** P3
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** TanStack Query / Cache, PWA / Mobile-first
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe E ; [`notifications_realtime_consolidation.md`](./notifications_realtime_consolidation.md)
- **Pourquoi pas maintenant :** edge case mobile ; threads commentaires rafraîchissent en session active
- **Questions précises à auditer :**
  - Au reconnect, quels query roots comment sont invalidés ?
  - `realtime_domain.md` §10 documente-t-il le gap ?
- **Risques à vérifier :** threads stale après background tab / perte réseau terrain
- **Fichiers probables à inspecter :** `apps/web/src/features/realtime/components/operational-realtime-provider.tsx`, `apply-operational-invalidation.ts`, `realtime/consumers.py`
- **Tests existants à inspecter / zones de test à vérifier :** `operational-realtime-provider.test.tsx` ; `realtime/tests/test_broadcast.py`

---

### OR-07 / OBS-07 — Processing-status : poll sans subject WS `observation`

- **IDs :** OR-07, OBS-07
- **Priorité :** P3
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** PWA / Mobile-first, TanStack Query / Cache
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`observation_refresh_consolidation.md`](./observation_refresh_consolidation.md)
- **Pourquoi pas maintenant :** poll 2s + invalidation signal pipeline = redondant mais safe (WONT_FIX_NOW echo) ; volume dev faible
- **Questions précises à auditer :**
  - Quelle fréquence poll réelle sur mobile ?
  - Un subject `observation` WS réduirait-il les requêtes sans élargir la surface sécurité ?
  - Quels événements `signal.*` couvrent déjà la fin de pipeline ?
- **Risques à vérifier :** batterie/réseau terrain ; UX latence perçue processing
- **Fichiers probables à inspecter :** `apps/web/src/features/observations/` (processing panel), `observations/api/views.py`, `realtime/ws_payloads.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_processing_status_api.py` ; `realtime/tests/test_observation_pipeline_invalidation.py`

---

## 4. Celery / Async

### C-03 / OR-02 — Retry Celery pipeline : output LLM divergent

- **IDs :** C-03, OR-02
- **Priorité :** P1/P2
- **Domaine principal :** Celery / Async
- **Domaines secondaires :** Database / ORM (duplicate signals)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe A ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md) ; [`observation_refresh_consolidation.md`](./observation_refresh_consolidation.md)
- **Pourquoi pas maintenant :** retry même output testé ; chemin divergent non testé ; design policy = M
- **Questions précises à auditer :**
  - Que se passe-t-il si le retry LLM produit une clé d’agrégation différente ?
  - Un output intermédiaire est-il persisté avant `apply_pipeline_output` ?
  - La contrainte unique active aggregation (SIG-03) suffit-elle à garantir l’idempotence ?
- **Risques à vérifier :** signaux dupliqués ; état `ObservationProcessing` incohérent
- **Fichiers probables à inspecter :** `signals/tasks.py`, `signals/services.py`, `ai/observation_pipeline.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_observation_pipeline_recovery.py` (`test_provider_unavailable_then_retry_completes_without_duplicate_signals`) ; `test_double_pipeline_on_processed_is_noop`

---

### CL-08 — Horizon Celery global sans sharding per-establishment

- **IDs :** CL-08
- **Priorité :** P2
- **Domaine principal :** Celery / Async
- **Domaines secondaires :** Realtime / Event-driven (materialization timing)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe C ; [`checklist_consolidation.md`](./checklist_consolidation.md)
- **Pourquoi pas maintenant :** job global suffisant pilote ; sharding = M
- **Questions précises à auditer :**
  - Quelle durée et quelle fréquence du beat horizon ?
  - Un établissement volumineux bloque-t-il les autres dans la même tâche ?
  - Existe-t-il retry/idempotence par assignment ?
- **Risques à vérifier :** materialization en retard ; timeout Celery ; gap pre-`visible_from` (lien CL-04)
- **Fichiers probables à inspecter :** `checklists/tasks.py`, `checklists/materialization.py`, Beat schedule dans `config/settings.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_materialization_services.py` ; tests concurrency materialization

---

### EF-02 — Boucle materialization per-assignment non batchée

- **IDs :** EF-02
- **Priorité :** P2
- **Domaine principal :** Celery / Async
- **Domaines secondaires :** Database / ORM
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe B ; [`execution_feed_consolidation.md`](./execution_feed_consolidation.md)
- **Pourquoi pas maintenant :** couplé à R3/EF-01 ; batching = M après stratégie materialization
- **Questions précises à auditer :**
  - Combien de requêtes `_existing_occurrence_dates_for_assignment` par feed GET ?
  - Un batch cross-assignment est-il possible sans casser l’idempotence ?
- **Risques à vérifier :** amplification SQL sur établissements multi-assignments
- **Fichiers probables à inspecter :** `checklists/materialization.py`, `actions/execution_feed.py`
- **Tests existants à inspecter / zones de test à vérifier :** query-count tests execution feed ; `test_materialization_services.py`

---

### AI F6 / R7 — Prompt pipeline : taxonomy + contexte signaux actifs

- **IDs :** AI F6, R7 (global)
- **Priorité :** P2
- **Domaine principal :** Celery / Async
- **Domaines secondaires :** API / OpenAPI (contrat pipeline), CI / DevEx / Docs (métriques)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R7 ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md)
- **Pourquoi pas maintenant :** volume dev acceptable ; coût/latence à mesurer à l’échelle
- **Questions précises à auditer :**
  - Quelle taille médiane/p95 de `input_payload_bytes` / tokens par appel ?
  - `MAX_ACTIVE_SIGNALS_CONTEXT = 20` est-il borné correctement pour établissements denses ?
  - La taxonomy complète est-elle renvoyée à chaque appel ?
- **Risques à vérifier :** coût OpenAI ; timeout provider ; dégradation throughput observation→signal
- **Fichiers probables à inspecter :** `ai/observation_pipeline.py`, `signals/services.py` (`build_pipeline_input`, `_build_active_signals_context`)
- **Tests existants à inspecter / zones de test à vérifier :** `ai/tests/test_observation_pipeline_provider.py` ; `ai/tests/test_observation_pipeline_schema.py`

---

### EF-07 — Baselines query feed mixed/heavy

- **IDs :** EF-07
- **Priorité :** P2
- **Domaine principal :** Celery / Async
- **Domaines secondaires :** CI / DevEx / Docs (`testing/query_baseline.py`), Database / ORM
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe B ; [`execution_feed_consolidation.md`](./execution_feed_consolidation.md)
- **Pourquoi pas maintenant :** baselines à établir **après** stratégie materialization (R3) ; sinon faux positifs
- **Questions précises à auditer :**
  - Quelles constantes dans `testing/query_baseline.py` couvrent feed peuplé mixte action+checklist ?
  - Les baselines actuels (empty, three actions) suffisent-ils à détecter régression post-decouple ?
- **Risques à vérifier :** régression perf non détectée ; baseline trop laxiste ou trop stricte
- **Fichiers probables à inspecter :** `apps/api/houston/testing/query_baseline.py`, `actions/tests/test_execution_feed_api.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_execution_feed_query_count_with_three_actions` ; `EXECUTION_FEED_EMPTY_MAX_QUERIES`

---

## 5. TanStack Query / Cache

### NR-09 — Hubs `reporting` / `workspace` non invalidés par WS opérationnel

- **IDs :** NR-09
- **Priorité :** P3
- **Domaine principal :** TanStack Query / Cache
- **Domaines secondaires :** Realtime / Event-driven, Frontend Architecture
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe E ; [`notifications_realtime_consolidation.md`](./notifications_realtime_consolidation.md) §6
- **Pourquoi pas maintenant :** audit hub freshness recommandé comme prochain ; pas de bug sécurité
- **Questions précises à auditer :**
  - Quels `queryKey` roots `reporting` et `workspace` existent ?
  - Quels événements WS opérationnels devraient les invalider vs refetch manuel ?
  - Un utilisateur sur `/reporting` voit-il des KPIs stale pendant que le feed terrain se rafraîchit ?
- **Risques à vérifier :** données opérationnelles périmées en hub ; confusion utilisateur multi-écran
- **Fichiers probables à inspecter :** `apps/web/src/lib/query-invalidation.ts`, `features/realtime/lib/apply-operational-invalidation.ts`, routes reporting/workspace
- **Tests existants à inspecter / zones de test à vérifier :** `operational-realtime-provider.test.tsx` ; tests hooks reporting/workspace s’ils existent

---

## 6. Frontend Architecture

### OB-03 — Wizard onboarding : couverture tests composant

- **IDs :** OB-03
- **Priorité :** P1
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** PWA / Mobile-first
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md)
- **Pourquoi pas maintenant :** tests API onboarding FIXED (OB-02) ; UI wizard = M, pas bloquant MVP fonctionnel
- **Questions précises à auditer :**
  - Quels composants wizard (activation card, resume, routing) n’ont aucun test Vitest ?
  - Les états loading/error/unauthorized sont-ils explicites sur mobile ?
- **Risques à vérifier :** régression routing onboarding ; blocage activation non détecté
- **Fichiers probables à inspecter :** `apps/web/src/features/onboarding/` (pages, components, `manual-v2-proposal.ts`)
- **Tests existants à inspecter / zones de test à vérifier :** tests onboarding existants sous `features/onboarding/` ; `npm test` inventory

---

### OB-06 — `_ONBOARDING_CONTINUE_ROLES` dupliqué

- **IDs :** OB-06
- **Priorité :** P2
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI (bootstrap selectors)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md)
- **Pourquoi pas maintenant :** duplication backend access/selectors ; pas de drift constaté en tests
- **Questions précises à auditer :**
  - Les deux listes de rôles sont-elles identiques byte-for-byte ?
  - Le frontend dérive-t-il sa logique continue depuis bootstrap ou copie locale ?
- **Risques à vérifier :** director/owner voit continue bloqué ou inverse
- **Fichiers probables à inspecter :** `establishments/access.py` (~L161–165), `accounts/selectors.py` (~L16–20)
- **Tests existants à inspecter / zones de test à vérifier :** tests bootstrap ; `can_continue_onboarding` paths

---

### OB-07 — Double autorité step wizard (client vs serveur)

- **IDs :** OB-07
- **Priorité :** P2
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`onboarding_observation_ai_consolidation.md`](./onboarding_observation_ai_consolidation.md) ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) §3 (manual-v2-proposal)
- **Pourquoi pas maintenant :** un seul client web ; pas de second client mobile natif
- **Questions précises à auditer :**
  - Quand `deriveWizardStepFromState` et `session.current_step` divergent, quelle UI s’affiche ?
  - Le serveur est-il autorité finale sur activation readiness ?
- **Risques à vérifier :** étapes incohérentes après refresh ; proposal client hors sync
- **Fichiers probables à inspecter :** `manual-v2-proposal.ts`, `OnboardingHeroCard`, `establishments/api/serializers.py` (session)
- **Tests existants à inspecter / zones de test à vérifier :** tests onboarding API ; absence de tests composant (lien OB-03)

---

### FE-02 — Route `/checklists/new` sans page guard

- **IDs :** FE-02
- **Priorité :** P2
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`rbac_security_audit.md`](./rbac_security_audit.md)
- **Pourquoi pas maintenant :** API 403 enforce ; UX polish S
- **Questions précises à auditer :**
  - Quel guard pattern utilisent les routes voisines (execution create, team) ?
  - Le bootstrap expose-t-il `can_create_checklist_template` exploitable en route guard ?
- **Risques à vérifier :** formulaire visible puis erreur API ; frustration utilisateur
- **Fichiers probables à inspecter :** routes checklist dans `apps/web/src/`, `features/checklists/pages/`
- **Tests existants à inspecter / zones de test à vérifier :** `execution-create-menu.test.ts` (pattern hints) ; tests routing s’ils existent

---

### FE-03 — Route `/team` reachable sans management hints

- **IDs :** FE-03
- **Priorité :** P2
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`rbac_security_audit.md`](./rbac_security_audit.md)
- **Pourquoi pas maintenant :** API enforce invite/manage ; polish navigation S
- **Questions précises à auditer :**
  - Staff atteint-il `/team` et voit-il des actions désactivées ou des erreurs ?
  - Les hints bootstrap `can_invite` / `can_manage_memberships` sont-ils consommés ailleurs ?
- **Risques à vérifier :** UX trompeuse ; appels API inutiles
- **Fichiers probables à inspecter :** `features/auth/` (team pages), bootstrap types, route config
- **Tests existants à inspecter / zones de test à vérifier :** tests auth bootstrap ; tests invitation RBAC

---

### FE-04 / R6 — Miroir RBAC frontend incomplet (manager)

- **IDs :** FE-04, R6 (global)
- **Priorité :** P2
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R6 ; [`rbac_security_audit.md`](./rbac_security_audit.md)
- **Pourquoi pas maintenant :** UI owner/director gated aujourd’hui ; backend rejette ; drift maintenance
- **Questions précises à auditer :**
  - Quelles matrices dans `membership-rbac.ts` / `invitation-rbac.ts` divergent du backend ?
  - Le bootstrap pourrait-il remplacer les copies locales pour les rôles cibles invite ?
- **Risques à vérifier :** option UI affichée + API 403 ; support burden
- **Fichiers probables à inspecter :** `features/auth/lib/membership-rbac.ts`, `invitation-rbac.ts`, `establishments/services.py` (invite rules)
- **Tests existants à inspecter / zones de test à vérifier :** `membership-rbac.test.ts` ; `invitation-rbac.test.ts` (valident copies frontend seulement)

---

### OR-09 — `ReportPage` sans tests composant / intégration

- **IDs :** OR-09
- **Priorité :** P3
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** PWA / Mobile-first
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe F ; [`observation_refresh_consolidation.md`](./observation_refresh_consolidation.md)
- **Pourquoi pas maintenant :** chemins API testés (OR-04) ; UI dual-path submit = M
- **Questions précises à auditer :**
  - Quels états (checklist context, processing panel, error) ne sont pas couverts ?
  - La page respecte-t-elle mobile-first (pas de scroll horizontal, états explicites) ?
- **Risques à vérifier :** régression submit dual-path ; processing panel silencieux
- **Fichiers probables à inspecter :** `apps/web/src/features/observations/pages/ReportPage` (ou équivalent)
- **Tests existants à inspecter / zones de test à vérifier :** `test_observation_api.py`, `test_processing_status_api.py` (backend) ; absence Vitest documentée

---

### CL-10 — Hub checklist : filtre `business_unit_id` + tests frontend

- **IDs :** CL-10
- **Priorité :** P3
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe C ; [`checklist_consolidation.md`](./checklist_consolidation.md)
- **Pourquoi pas maintenant :** P3 polish ; hub fonctionne sans filtre BU explicite côté UI
- **Questions précises à auditer :**
  - L’API hub supporte-t-elle `business_unit_id` non consommé par le frontend ?
  - Quelle couverture test hub page vs API ?
- **Risques à vérifier :** liste hub trop large pour manager scoped ; delete hint trap (CL-03 FIXED)
- **Fichiers probables à inspecter :** `features/checklists/pages/` (hub), `checklists/api.ts`, `checklists/selectors.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_template_assignment_permission_hints_api.py` ; hub API tests

---

## 7. PWA / Mobile-first

PWA n’a pas d’item DEFER autonome, mais reste un **audit transversal obligatoire** après Frontend Architecture (étape 6 de l’ordre recommandé). Relecture transversale sur les items des §§ 3, 5 et 6 :

| IDs liés | Angle PWA à vérifier |
|----------|----------------------|
| OR-07 / OBS-07 | Impact poll 2s batterie/réseau ; états offline processing |
| NR-08 | Reconnect background tab mobile |
| OB-03 | Layout wizard phone-first ; error/empty states |
| OR-09 | `ReportPage` sur viewport étroit |

---

## 8. CI / DevEx / Docs

### R10 — Docs phase / archive stale

- **IDs :** R10
- **Priorité :** P3
- **Domaine principal :** CI / DevEx / Docs
- **Domaines secondaires :** Realtime / Event-driven (doc contradiction)
- **Source :** [`feature_audit_closure.md`](./feature_audit_closure.md) Groupe G ; [`global_architecture_mapping.md`](./global_architecture_mapping.md) R10
- **Pourquoi pas maintenant :** hygiene S ; `docs/README.md` hiérarchise déjà code > docs
- **Questions précises à auditer :**
  - `product_operating_model.md` Phase 8C reflète-t-il realtime opérationnel implémenté ?
  - `docs/archive/codex/` duplique-t-il des domaines actifs ?
- **Risques à vérifier :** agents/humains suivent doc obsolète
- **Fichiers probables à inspecter :** `docs/product/product_operating_model.md`, `docs/README.md`, `docs/archive/`
- **Tests existants à inspecter / zones de test à vérifier :** aucun ; vérification manuelle hiérarchie docs

---

## 9. Décisions post-phase 2 (ouverts — à auditer, pas à corriger)

Extrait de [`feature_audit_decisions.md`](./feature_audit_decisions.md). Ces items **ne sont pas** des `DEFER_PHASE_2` ; ils documentent des gates produit/UX pouvant attendre après les audits infra. L’audit doit **trancher ou confirmer le défaut MVP**, sans plan d’action code.

### ACT-03 — UI reassign / due-at

- **IDs :** ACT-03
- **Priorité :** P2 (produit)
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI (hooks existants)
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : reassign first, due-at defer
- **Pourquoi pas maintenant :** slice produit optionnelle ; backend + hooks livrés
- **Questions précises à auditer :**
  - Les hooks reassign/due-at sont-ils branchés sur aucun composant detail ?
  - Quel gap UX pour manager vs staff sur due-at ?
- **Risques à vérifier :** due-at modifié uniquement via API brute ; reassign non découvrable
- **Fichiers probables à inspecter :** `features/actions/hooks.ts`, pages action detail
- **Tests existants à inspecter / zones de test à vérifier :** `test_action_services.py` (backend reassign) ; absence tests UI

---

### ACT-08 — UX multi-assignee au-delà du footer

- **IDs :** ACT-08
- **Priorité :** P2/P3 (produit)
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** —
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : footer minimal `accepted_by`
- **Pourquoi pas maintenant :** polish post-MVP ; modèle backend multi-assignee livré
- **Questions précises à auditer :**
  - Quelles surfaces (feed card, detail) n’affichent pas la liste assignees ?
  - La course accept est-elle compréhensible avec footer seul ?
- **Risques à vérifier :** confusion terrain sur qui a accepté ; double accept affiché
- **Fichiers probables à inspecter :** `execution-action-card.tsx`, action detail components
- **Tests existants à inspecter / zones de test à vérifier :** `execution-action-card.test.tsx`

---

### CL-06 — UI activate/deactivate template

- **IDs :** CL-06
- **Priorité :** P2 (produit)
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** API / OpenAPI
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : defer UI
- **Pourquoi pas maintenant :** endpoints backend existent ; CL-05 FIXED (dead hooks retirés)
- **Questions précises à auditer :**
  - Quels endpoints activate/deactivate sont exposés OpenAPI sans UI ?
  - Quel impact opérationnel sans UI (templates toujours actifs par défaut) ?
- **Risques à vérifier :** templates obsolètes restent actifs ; confusion admin
- **Fichiers probables à inspecter :** `checklists/api/views.py`, template detail page
- **Tests existants à inspecter / zones de test à vérifier :** tests API template lifecycle

---

### EF-08 / CL-04 — Lazy vs proactive materialization pre-`visible_from`

- **IDs :** EF-08, CL-04
- **Priorité :** P2 (produit/stratégie)
- **Domaine principal :** Realtime / Event-driven
- **Domaines secondaires :** Celery / Async
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : lazy accepté ; lien R3
- **Pourquoi pas maintenant :** dépend stratégie materialization phase 2 ; pilote mono-shift
- **Questions précises à auditer :**
  - Quel gap WS/feed avant `visible_from` en multi-shift ?
  - Le beat horizon comble-t-il le gap dans les scénarios pilote ?
- **Risques à vérifier :** supervision ne voit pas exécution avant fenêtre visible
- **Fichiers probables à inspecter :** `materialization.py`, `execution_feed.py`, `realtime_domain.md`
- **Tests existants à inspecter / zones de test à vérifier :** tests materialization visibility ; tests beat schedule

---

### NR-06 / D-02 — Invalidation parent feeds sur `comment.*`

- **IDs :** NR-06, D-02
- **Priorité :** P2 (produit)
- **Domaine principal :** TanStack Query / Cache
- **Domaines secondaires :** Realtime / Event-driven
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : threads commentaires only
- **Pourquoi pas maintenant :** tradeoff bruit vs fraîcheur ; pas de bug sécurité
- **Questions précises à auditer :**
  - Quels query roots signal/action feed ne sont pas invalidés sur `comment.created` ?
  - Quelle fréquence commentaires rend le stale perceptible ?
- **Risques à vérifier :** compteur comments stale sur feed card ; detail à jour, liste non
- **Fichiers probables à inspecter :** `apply-operational-invalidation.ts`, `realtime/broadcast.py`, `comments/services.py`
- **Tests existants à inspecter / zones de test à vérifier :** `realtime/tests/` comment invalidation ; `operational-realtime-provider.test.tsx`

---

### D-04B — Retry / outbox notifications post-commit

- **IDs :** D-04B
- **Priorité :** P2 (produit/infra)
- **Domaine principal :** Celery / Async
- **Domaines secondaires :** Realtime / Event-driven
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : log only (NR-05 FIXED)
- **Pourquoi pas maintenant :** Lot1 in-app ; pas de SLA delivery exigé
- **Questions précises à auditer :**
  - Quelle perte notification si `deliver()` échoue après commit ?
  - Un outbox serait-il requis pour Lot2 push/email ?
- **Risques à vérifier :** notification manquante silencieuse ; double delivery si retry naïf
- **Fichiers probables à inspecter :** `notifications/scheduling.py`, `notifications/services.py`
- **Tests existants à inspecter / zones de test à vérifier :** `test_scheduling_failure_logging.py`

---

### SIG-06 — Tabs admin Ma zone ≡ Vue globale

- **IDs :** SIG-06
- **Priorité :** P2 (cosmétique)
- **Domaine principal :** Frontend Architecture
- **Domaines secondaires :** —
- **Source :** [`feature_audit_decisions.md`](./feature_audit_decisions.md) ; défaut MVP : unifier labels ; hide toggle optionnel
- **Pourquoi pas maintenant :** pas d’impact sécurité ; données identiques
- **Questions précises à auditer :**
  - Les deux tabs déclenchent-ils les mêmes query params / `view_mode` ?
  - Quelle confusion utilisateur est mesurable ?
- **Risques à vérifier :** aucun sécurité ; clutter UI admin
- **Fichiers probables à inspecter :** `features/signals/pages/`, signal feed tabs components
- **Tests existants à inspecter / zones de test à vérifier :** tests signal feed hooks s’ils existent

---

## Signaux transverses à vérifier

Sujets cités dans [`global_architecture_mapping.md`](./global_architecture_mapping.md) ou [`backend_core_architecture.md`](./backend_core_architecture.md) **sans** entrée `DEFER_PHASE_2` dédiée dans le registre closure. **Ils ne deviennent pas automatiquement des findings** — à confirmer ou infirmer lors de l’audit du domaine concerné.

| Signal | Source | Domaine d’audit confirmateur | Fichiers à inspecter |
|--------|--------|------------------------------|----------------------|
| **View-layer ORM drift** — ORM direct dans certaines views | backend_core § View-layer drift | API / OpenAPI | `comments/api/views.py`, `checklists/api/views.py`, `establishments/api/views.py` |
| **Helpers `_schedule_*_invalidation` dupliqués** | backend_core § Simplification | Realtime / Event-driven | `actions/services.py`, `signals/services.py`, `realtime/broadcast.py` |
| **Onboarding ORM dans establishments views** | backend_core § Simplification | API / OpenAPI | `establishments/api/views.py` (`_get_onboarding_establishment`) |
| **Urgence deadline côté client** (`action-display.ts`) | global § Known boundary drift | Frontend Architecture | `features/actions/lib/action-display.ts` |
| **Parité RBAC ligne-à-ligne non vérifiée** | global § Assumptions | API / OpenAPI + Frontend Architecture | Django `permissions.py` vs `membership-rbac.ts` |
| **Tests mock-heavy realtime/AI** — acceptable mais à inventorier | backend_core § Things not worth fixing now | CI / DevEx / Docs | `realtime/tests/`, `ai/tests/` |

---

**Changed:** Micro-ajustements doc — §1 note backend boundaries (sans phase séparée) ; §7 PWA audit transversal obligatoire post–Frontend Architecture  
**Validated:** Compteurs inchangés ; sujets fermés non rouverts  
**Risks / not verified:** `make verify` non exécuté ; note boundaries non revalidée ligne-à-ligne contre `backend_core_architecture.md` dans ce passage
