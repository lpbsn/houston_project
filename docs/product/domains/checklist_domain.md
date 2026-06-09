# Checklist Domain

Status: authoritative
Last reviewed: 2026-06-09
Implementation status: **Lots 2–7 implemented** — modèle unifié, bibliothèque unique, feed `+`, cleanup personal/shared, hardening global validé (2026-06-09).

Historical reference only (not active product truth): [`docs/archive/codex/houston_checklist_domain.md`](../../archive/codex/houston_checklist_domain.md).

## 1. Purpose

Checklist owns Houston's routine execution structure:

- **Checklists enregistrées** — modèles réutilisables (`ChecklistTemplate` + tâches), visibles dans la **Bibliothèque de checklists**
- **Flash To-do** — listes ponctuelles terrain sans modèle (`ChecklistExecution` seule)
- **Affectations planifiées** — `ChecklistAssignment` (récurrence, matérialisation) pour routines récurrentes
- Exécutions runtime et tâches runtime avec snapshots
- Complétion, skip et handoff Observation côté backend

Checklist is a routine domain. It is not Action, Signal, or Observation.

Checklist does not own:

- Signal creation or Action lifecycle
- feed sorting, filtering, pagination, or projection rules (owned by Feed domain)
- notification routing (deferred)
- realtime transport
- comments behavior
- RBAC internals (`MembershipScope` is defined in RBAC domain)
- raw Observation privacy policy

## 2. Vocabulaire produit

### Termes autorisés (UI et docs actives)

| Terme | Signification |
| --- | --- |
| **Checklist** | Domaine unique ; pas de sous-type produit |
| **Checklist enregistrée** | Modèle réutilisable en bibliothèque (`ChecklistTemplate`) |
| **Flash To-do** | Exécution ponctuelle sans modèle |
| **Bibliothèque de checklists** | Liste des checklists enregistrées accessibles (une seule bibliothèque) |
| **Badge Process** | Label UX : checklist plus officielle / process interne |
| **Badge To-do** | Label UX : checklist plus souple / terrain / réutilisable |

### Termes interdits (produit actif)

Ne plus utiliser comme concept courant :

- checklist personnelle / personal checklist
- checklist partagée / shared checklist
- `checklist_type` = personal | shared (concept produit ; champ technique en cours de suppression)
- deux bibliothèques (Process vs To-do, shared vs personal)
- onglets structurels lourds Process / To-do (un **badge + filtre** suffit)

### Règle badge

- `Process` et `To-do` sont le **même objet métier** (`ChecklistTemplate`).
- Le badge est **uniquement UX** ; il ne crée pas deux modèles, permissions, flows, tables ou endpoints.
- Le badge **ne modifie jamais le RBAC**.
- Badge par défaut à la création d'une checklist enregistrée : **`todo`**.

## 3. Concepts produit

### 3.1 Checklist enregistrée

- Stockée comme `ChecklistTemplate` + `ChecklistTaskTemplate`
- Visible dans la bibliothèque
- Réutilisable et assignable (exécution ponctuelle ou via `ChecklistAssignment`)
- Badge `process` ou `todo`
- `business_unit` **obligatoire**
- Modifiable / supprimable selon RBAC (§9)

### 3.2 Flash To-do

- Créé rapidement depuis le **Feed Exécution `+`**
- Crée **uniquement** une `ChecklistExecution` (et snapshots de tâches)
- **Ne crée aucun** `ChecklistTemplate`
- **N'apparaît jamais** dans la bibliothèque
- Visible dans le Feed Exécution tant que `status IN (assigned, in_progress)`
- Disparaît du feed principal une fois terminal : `done` ou `canceled`
- Peut rester en base pour audit minimal ; pas visible comme checklist active ni modèle réutilisable
- `execution_source = flash_todo`
- `checklist_template = null`
- `visible_from = null` (visible immédiatement)
- `end_at` optionnel

### 3.3 Séparation Template → Assignment → Execution

- **Template** : définition réutilisable (checklist enregistrée)
- **Assignment** : planification / récurrence (optionnel ; conservé MVP)
- **Execution** : instance opérationnelle snapshotée (feed terrain)

Sources d'exécution (`execution_source`) :

| Valeur | Origine |
| --- | --- |
| `flash_todo` | Flash To-do ; pas de template |
| `template` | Lancement ponctuel depuis checklist enregistrée (`POST .../templates/{id}/executions/` ou `assign_now` à la création) |
| `assignment` | Occurrence matérialisée depuis `ChecklistAssignment` |

## 4. MVP Scope

- Un seul domaine Checklist (plus de personal/shared).
- `ChecklistTemplate` : checklist enregistrée ; `badge` `process` | `todo` ; `business_unit` requis ; `status` `active` | `inactive`.
- `ChecklistAssignment` : `active` | `inactive` ; planification + récurrence hebdomadaire simple (conservé).
- `ChecklistExecution` : `assigned` | `in_progress` | `done` | `canceled` ; `execution_source` ; template nullable.
- `ChecklistTaskExecution` : `pending` | `done` | `skipped` | `observation_created`.
- Snapshots obligatoires à la création / matérialisation d'exécution.
- Pas d'endpoint `start` — passage `assigned` → `in_progress` au premier événement tâche.
- Handoff Observation depuis tâche (pipeline async existant).
- Exécutions checklist dans Execution Feed (`item_type: checklist`).
- **Profil → Gérer les checklists** : bibliothèque unique + gestion assignments sur les modèles.
- **Feed Exécution `+`** : Action / Flash To-do / Checklist (voir §3.19).
- Pas de commentaires checklist en MVP.

**Migration DEV/test (Lots 2A–2B)** : suppression **destructive** de toutes les données `personal` legacy (`checklist_type = personal`) — pas de conversion, pas de préservation pilot. Environnement DEV/test uniquement.

Current code truth :

- Backend: [`apps/api/houston/checklists/`](../../../apps/api/houston/checklists/)
- OpenAPI: [`apps/api/schema.yml`](../../../apps/api/schema.yml)
- Frontend bibliothèque : [`apps/web/src/features/checklists/`](../../../apps/web/src/features/checklists/) — routes `/checklists`, `/checklists/new`, `/checklists/{id}`
- Feed card : [`execution-checklist-card.tsx`](../../../apps/web/src/features/execution/components/execution-checklist-card.tsx) — `execution_source` + `badge`

## 5. Décisions définitives MVP

### 5.1 Statuts

| Object | MVP statuses | Forbidden names |
| --- | --- | --- |
| `ChecklistTemplate` | `active`, `inactive` | `draft`, `archived` |
| `ChecklistAssignment` | `active`, `inactive` | `draft`, `archived` |
| `ChecklistExecution` | `assigned`, `in_progress`, `done`, `canceled` | `open`, `completed`, `inactive`, `archived` |
| `ChecklistTaskExecution` | `pending`, `done`, `skipped`, `observation_created` | — |

### 5.2 Complétion

A task is **treated** when its status is `done`, `skipped`, or `observation_created`.

`ChecklistExecution` becomes `done` when **all** task executions are treated.

`observation_created` counts as treated for execution completion.

### 5.3 Pas de endpoint `start`

`ChecklistExecution` passes from `assigned` to `in_progress` on the **first** user task event: `mark_done`, `skip`, or `create_observation_from_task`.

### 5.4 Modèle cible (post-refonte)

```txt
ChecklistTemplate                    # checklist enregistrée uniquement
  establishment_id
  created_by
  business_unit                      # required
  title, description
  badge = process | todo               # UX only; default todo
  status = active | inactive

ChecklistTaskTemplate
  checklist_template_id
  task, position

ChecklistAssignment                  # planification / récurrence (conservé)
  checklist_template_id
  assigned_to, assigned_by
  business_unit                      # snapshot from template
  start_date, end_date
  start_at, end_at                   # daily TimeField; end_at > start_at; no overnight
  recurrence_days                  # nullable; empty = one-shot
  status = active | inactive

ChecklistExecution
  checklist_template_id              # nullable (flash_todo)
  checklist_assignment_id            # nullable (template / flash_todo)
  execution_source = flash_todo | template | assignment
  establishment_id
  assigned_to, assigned_by
  business_unit                      # required (snapshot)
  occurrence_date                    # nullable; idempotence assignment
  start_at, end_at, visible_from     # snapshots; flash: visible_from null
  template_title, template_description
  status, last_activity_at
```

**Champs supprimés (cible)** : `checklist_type` sur template et execution.

### 5.5 BusinessUnit / RBAC

Use `MembershipScope` on **BusinessUnit** only.

- `ChecklistTemplate.business_unit` is **required** for all registered templates.
- `ChecklistExecution.business_unit` is a snapshot (required).
- Assignee eligibility : assigné doit couvrir le `business_unit` de la checklist via `MembershipScope` (sauf Owner/Director : tout membre actif de l'établissement).
- User search : `GET .../users/search/?business_unit_id=` pour pickers assigné.

Voir §9 pour la matrice complète.

### 5.6 Scheduling — assignments (conservé)

**Establishment timezone (MVP)** :

- `Establishment.timezone` IANA (default `Europe/Paris` pilot).
- Assignment dates/times are establishment-local wall clock.
- Materialization stores aware datetimes in UTC.

**`ChecklistAssignment`** :

- Period: `start_date`, `end_date` (`end_date >= start_date`).
- Daily times: `start_at`, `end_at` (`end_at > start_at`, no overnight).
- `recurrence_days` : weekly simple ; empty/null = one-shot on `start_date`.
- Assignment stays `active` after `end_date` until deactivated ; materialization stops beyond `end_date`.

**Executions matérialisées (`execution_source = assignment`)** :

- `visible_from = execution.start_at - 1 hour`
- Feed inclusion: `status IN (assigned, in_progress)` AND `now >= visible_from`
- `end_at` overdue does **not** remove from feed — only `done` / `canceled`

**Executions `flash_todo` et `template`** :

- `visible_from = null` (immédiat)
- `start_at` nullable sauf si défini à la création

### 5.7 Récurrence et matérialisation (conservé)

Horizon 14 jours :

1. **Eager** — première occurrence à la création d'assignment
2. **Lazy** — `ensure_visible_executions_materialized` sur lecture execution-feed
3. **Celery Beat** (optionnel) — `materialize_checklist_assignments_horizon_task` daily

### 5.8 Observation depuis tâche (conservé)

- Min 10 caractères ; pipeline async Observation → Signal
- Task → `observation_created` ; compte comme traité
- Pas de texte Observation brut sur surfaces checklist
- Handoff : `Observation.origin = checklist_task`

### 5.9 Réordonnancement des tâches (conservé)

- `position` requis ; reorder API MVP

### 5.10 Exécutions concurrentes

- Plusieurs exécutions actives par template (assignments / lancements ponctuels / flash distincts).
- Plus de règle « une seule exécution active par template personal » (concept supprimé).

### 5.11 Template / Assignment inactive (conservé)

- Template `inactive` : bloque nouveaux assignments et nouvelles exécutions depuis modèle ; exécutions existantes inchangées.
- Assignment `inactive` : stoppe matérialisation future.
- `PATCH` assignment : sync snapshots sur exécutions `assigned` encore valides ; cancel hors schedule.
- `POST .../deactivate/` assignment : règles 409 / cancel `assigned` inchangées.
- `DELETE` template : Owner/Director ; 409 si exécution active ; historique détaché (`checklist_template = null`).

### 5.12 Annulation exécution

| `execution_source` | Qui peut cancel |
| --- | --- |
| `flash_todo`, `template` | **Assigné** ; Owner/Director (établissement) ; Manager si `business_unit` dans scope |
| `assignment` | Idem (exécution matérialisée) |

**Staff** : peut cancel si **assigné** ; ne peut pas cancel l'exécution d'un **tiers**.

### 5.13 Snapshots (conservé)

À la création d'exécution (flash, template, ou matérialisation) :

- `template_title`, `template_description`
- `business_unit`, `assigned_to`, `assigned_by`
- `start_at`, `end_at`, `visible_from` (selon source)
- par tâche : `task`, `position`

### 5.14 Checklist vide (conservé)

- Template sans tâche : seulement en `inactive`
- Activation interdite sans ≥1 tâche
- Création exécution / assignment interdite sans tâches sur template `active`

### 5.15 Tri Execution Feed (conservé)

Checklists among themselves : `last_activity_at desc`. Page merge : checklists first, Actions fill slots ([`execution_feed.py`](../../../apps/api/houston/actions/execution_feed.py)).

### 5.16 UX — Profil vs Feed Exécution `+`

**Profil → Gérer les checklists** (tous rôles actifs) :

- **Bibliothèque de checklists** unique — checklists enregistrées accessibles selon RBAC
- Filtres : badge (Tous / Process / To-do), pôle, créées par moi
- Détail modèle : tâches, assignments planifiés, utiliser / assigner
- **Jamais** de Flash To-do dans la bibliothèque

**Feed Exécution `+`** (mobile-first) :

| Entrée | Comportement |
| --- | --- |
| **Action** | Inchangé (Owner/Director/Manager) |
| **Flash To-do** | Flow court → `POST .../checklist-executions/flash-todo/` |
| **Checklist** | Choix : **Créer une checklist** / **Utiliser une checklist existante** |

**Créer une checklist enregistrée** (depuis `+` ou bibliothèque) :

- Titre, description optionnelle, tâches (≥1), BU, badge (default `todo`)
- Assigner maintenant : oui/non ; si oui : assigné + `end_at` optionnel
- `POST .../checklist-templates/` transactionnel (`assign_now` crée aussi exécution)

**Utiliser une checklist existante** :

- Choisir modèle accessible, assigné, `end_at` optionnel
- `POST .../checklist-templates/{id}/executions/`

## 6. Hors MVP

- Endpoint `start` pour executions
- Statuts `draft`, `archived`, `completed`, `open` pour exécutions
- Modèle ou domaine `PersonalChecklist` / distinction shared/personal
- Deux bibliothèques ou permissions selon badge Process/To-do
- Approbation modèles, marketplace, commentaires checklist, preuve photo obligatoire
- Validation manager à la complétion
- RRULE avancé, notifications checklist (Phase 6+)
- Realtime checklist (deferred)
- Historique UI des exécutions terminées (accès par ID seulement aujourd'hui)

## 7. Core Invariants

- Badge ne pilote jamais RBAC.
- Flash To-do ne crée jamais de template.
- Bibliothèque = templates enregistrés uniquement.
- Recurrence vit sur `ChecklistAssignment`, pas sur `ChecklistExecution`.
- Backend owns all lifecycle transitions via explicit service methods.
- Single-assignee per execution et per assignment.
- `end_at` ne retire pas du feed actif — seuls `done` / `canceled`.
- Establishment scoping mandatory.
- No raw Observation text on checklist surfaces.

## 8. Main Objects (cible post-refonte)

Voir §5.4. Inspect [`models.py`](../../../apps/api/houston/checklists/models.py) before claiming field names match production code during migration.

## 9. Permissions

Establishment-scoped, backend-enforced. Helpers: [`permissions.py`](../../../apps/api/houston/checklists/permissions.py). UX hints: [`permission_hints.py`](../../../apps/api/houston/checklists/permission_hints.py) — **not authorization authority**.

### 9.1 Matrice cible

| Capability | Owner / Director | Manager | Staff |
| --- | --- | --- | --- |
| Profil — Bibliothèque de checklists | yes | yes | yes |
| Créer Flash To-do (scope BU) | yes (all BU) | yes, scoped BU | yes, scoped BU |
| Créer checklist enregistrée | yes (all BU) | yes, scoped BU | yes, scoped BU |
| Voir bibliothèque (modèles accessibles) | all establishment | scoped BU | scoped BU |
| Modifier checklist enregistrée | all | scoped BU | **own `created_by` only** |
| Supprimer checklist enregistrée | all | scoped BU | **own `created_by` only** |
| Utiliser / lancer exécution depuis modèle | all | scoped BU | scoped BU (même si autre auteur) |
| Gérer assignments (créer / PATCH / deactivate) | yes | scoped BU | no |
| Exécuter tâches (assigné) | if assignee | if assignee | if assignee |
| Annuler exécution | yes ; Manager scoped | scoped BU ; assigné | **assigné only** |
| Feed `+` — Action | yes | yes | no |
| Feed `+` — Flash To-do / Checklist | yes | yes | yes |

**Assigné** :

- Owner/Director : tout membre actif de l'établissement
- Manager/Staff : membre actif couvrant le `business_unit` de la checklist (`MembershipScope`)

### 9.2 Permission hints (cible)

| Resource | Hint keys (cible) |
| --- | --- |
| Template | `can_update`, `can_manage_tasks`, `can_activate`, `can_deactivate`, `can_delete`, `can_create_assignment`, `can_launch_execution` |
| Assignment | `can_update`, `can_deactivate` |
| Execution | `can_execute_tasks`, `can_cancel` |

Legacy hint `can_create_personal_execution` — **supprimé** (remplacé par `can_launch_execution`).

RBAC reference: [`rbac_permissions_domain.md`](rbac_permissions_domain.md).

## 10. API Surface

Inspect [`apps/api/schema.yml`](../../../apps/api/schema.yml) before claiming endpoints exist.

### 10.1 Endpoints cibles (refonte Lot 3)

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `checklist-templates/` | Bibliothèque (filtres `badge`, `business_unit_id`, `created_by_me`) / création enregistrée composite |
| GET, PATCH, DELETE | `checklist-templates/{id}/` | Detail / update / delete |
| POST | `checklist-templates/{id}/executions/` | Lancer exécution depuis modèle |
| POST | `checklist-executions/flash-todo/` | Créer Flash To-do (exécution seule) |
| POST | `checklist-templates/{id}/activate/` | Activate (≥1 task) |
| POST | `checklist-templates/{id}/deactivate/` | Deactivate |
| POST | `checklist-templates/{id}/tasks/` | Add task |
| PATCH, DELETE | `checklist-task-templates/{id}/` | Update / delete task |
| POST | `checklist-templates/{id}/tasks/reorder/` | Reorder |
| GET | `checklist-assignments/` | List active assignments |
| POST | `checklist-templates/{id}/assignments/` | Create assignment + first occurrence |
| GET, PATCH | `checklist-assignments/{id}/` | Detail / update schedule |
| POST | `checklist-assignments/{id}/deactivate/` | Deactivate assignment |
| GET | `checklist-executions/{id}/` | Detail + permission_hints |
| POST | `checklist-executions/{id}/cancel/` | Cancel |
| POST | `checklist-task-executions/{id}/mark-done/` | Mark done |
| POST | `checklist-task-executions/{id}/skip/` | Skip |
| POST | `checklist-task-executions/{id}/create-observation/` | Observation handoff |

**POST `checklist-templates/` payload cible (composite)** :

```json
{
  "title": "Fermeture restaurant",
  "description": "",
  "business_unit_id": "uuid",
  "badge": "process",
  "tasks": [{ "title": "Fermer caisse" }],
  "assign_now": true,
  "assigned_to": "uuid",
  "end_at": "2026-06-09T23:00:00+02:00"
}
```

**POST `checklist-executions/flash-todo/` payload cible** :

```json
{
  "title": "Vérifier la terrasse",
  "business_unit_id": "uuid",
  "assigned_to": "uuid",
  "end_at": "2026-06-09T18:00:00+02:00",
  "tasks": [{ "title": "Nettoyer les tables" }]
}
```

### 10.2 Endpoints legacy (supprimés Lot 6)

| Endpoint | Statut |
| --- | --- |
| `GET/POST checklist-templates/?type=shared\|personal` | **Supprimé** |
| `POST .../personal-executions/` | **Supprimé** |

Aucun comportement actif ne dépend de ces endpoints.

Execution Feed : `GET execution-feed/` — `item_type: action | checklist`.

## 11. Frontend Expectations (cible)

- **Bibliothèque unique** ; badge Process/To-do ; pas de sections personal/shared
- **Feed `+`** : Action / Flash To-do / Checklist
- Flash : un seul appel API `flash-todo/` — **pas** `quickCreatePersonalChecklistExecution` ni `personal-executions/`
- Feed card : label **Flash To-do** ou badge Process/To-do — **pas** Partagée/Personnelle
- TanStack Query + client OpenAPI généré
- Permission hints backend pour boutons modifier/supprimer/utiliser
- Lifecycle via commandes backend uniquement

## 12. Execution Feed integration

- Polymorphism `item_type: checklist`
- Feed item expose : title, progress, `execution_source`, `badge` (si template lié), `end_at`, `is_overdue`, BU label, status
- Inclusion : `status IN (assigned, in_progress)` AND visibility rules §5.6
- Terminal `done`/`canceled` excluded from active feed
- See [`feed_domain.md`](feed_domain.md)

## 13. Backend module architecture

| Module | Responsibility |
| --- | --- |
| `selectors.py` | Catalogues, feed querysets, detail |
| `materialization.py` | Assignment occurrences |
| `services.py` | Business commands |
| `permissions.py` | RBAC |
| `permission_hints.py` | UX hints |
| `execution_feed.py` (actions) | Polymorphic feed merge |

## 14. Migration DEV/test (Lots 2A–2B)

- **Autorisé** : suppression destructive de toutes les checklists `personal` (templates, exécutions, tâches)
- **Pas** de conversion personal → enregistrée
- Templates shared existants : `badge = process` par convention data migration ; nouvelles créations default `todo`
- Exécutions shared existantes : `execution_source = assignment` ou `template` selon présence d'assignment

## 15. AI Agent Notes

- Do not use `checklist_type` shared/personal as product truth after Lot 1.
- Do not branch RBAC on `badge`.
- Do not create separate Process/To-do models or endpoints.
- Flash To-do must not create `ChecklistTemplate`.
- Keep `ChecklistAssignment` + materialization unless explicitly removed in a future lot.
- Inspect `schema.yml` before claiming API shape.
- When changing APIs: update permissions, OpenAPI, generated clients, tests, and this document together.
- Archive [`houston_checklist_domain.md`](../../archive/codex/houston_checklist_domain.md) is historical only.
