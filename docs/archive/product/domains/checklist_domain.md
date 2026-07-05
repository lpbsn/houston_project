# Checklist Domain

Status: authoritative
Last reviewed: 2026-06-17
Implementation status: **Lot 0 (doc closure)** — modèle produit cible : checklist = processus opérationnel enregistré uniquement (`ChecklistTemplate`) ; Flash To-do et badge Process/To-do retirés du produit.

Historical reference only (not active product truth): [`docs/archive/codex/houston_checklist_domain.md`](../../archive/codex/houston_checklist_domain.md).

## 1. Purpose

Checklist owns Houston's routine execution structure:

- **Checklists enregistrées** — processus opérationnels réutilisables (`ChecklistTemplate` + tâches), visibles dans la **Bibliothèque de checklists**
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
| **Checklist** | Processus opérationnel enregistré ; un seul type produit (`ChecklistTemplate`) |
| **Checklist enregistrée** | Modèle réutilisable en bibliothèque (`ChecklistTemplate`) |
| **Bibliothèque de checklists** | Liste des checklists enregistrées accessibles (une seule bibliothèque) |
| **Lancer pour moi** | Lancement ponctuel d'une exécution depuis un modèle existant, assigné à soi-même (Staff) |

### Termes interdits (produit actif)

Ne plus utiliser comme concept courant :

- Flash To-do / flash todo / `flash_todo`
- checklist personnelle / personal checklist
- checklist partagée / shared checklist
- `checklist_type` = personal | shared (concept produit ; champ technique en cours de suppression)
- deux bibliothèques (Process vs To-do, shared vs personal)
- badge Process / badge To-do / distinction process vs todo
- onglets structurels lourds Process / To-do

## 3. Concepts produit

### 3.1 Checklist enregistrée

- Stockée comme `ChecklistTemplate` + `ChecklistTaskTemplate`
- Visible dans la bibliothèque
- Réutilisable et assignable (exécution ponctuelle ou via `ChecklistAssignment`)
- `business_unit` **obligatoire**
- Modifiable / supprimable selon RBAC (§9) — **Staff : lecture seule**

### 3.2 Flow produit

```txt
Créer le processus → enregistrer → lancer / assigner → exécuter
```

| Étape | Description | Qui |
| --- | --- | --- |
| **Créer** | Définir titre, description, tâches (≥1), pôle (`business_unit`) | Owner / Director / Manager (scope BU) |
| **Enregistrer** | `POST .../checklist-templates/` — modèle `active` ou `inactive` | Idem |
| **Lancer / assigner** | Exécution ponctuelle (`template`) ou planification (`ChecklistAssignment`) | Owner / Director / Manager : pour soi ou pour autrui ; **Staff : « Lancer pour moi » uniquement** |
| **Planifier (détail modèle)** | Bloc « Planification » sur la page détail : assigné, horaires, récurrence optionnelle ; CTA dynamique | Owner / Director / Manager : ponctuel ou récurrent ; Staff : ponctuel pour soi uniquement |
| **Exécuter** | Tâches runtime sur l'exécution assignée | Assigné |

Staff ne crée, ne modifie et ne supprime **aucun** processus. Staff ne crée **aucune** `ChecklistAssignment`.

### 3.3 Séparation Template → Assignment → Execution

- **Template** : définition réutilisable (checklist enregistrée)
- **Assignment** : planification / récurrence (optionnel ; conservé MVP)
- **Execution** : instance opérationnelle snapshotée (feed terrain)

Sources d'exécution (`execution_source`) :

| Valeur | Origine |
| --- | --- |
| `template` | Lancement ponctuel depuis checklist enregistrée (`POST .../templates/{id}/executions/` ou `assign_now` à la création) |
| `assignment` | Occurrence matérialisée depuis `ChecklistAssignment` |

Toute exécution est liée à un `ChecklistTemplate` (`checklist_template_id` requis).

## 4. MVP Scope

- Un seul domaine Checklist (plus de personal/shared, plus de Flash To-do).
- `ChecklistTemplate` : checklist enregistrée ; `business_unit` requis ; `status` `active` | `inactive`.
- `ChecklistAssignment` : `active` | `inactive` ; planification + récurrence hebdomadaire simple (conservé).
- `ChecklistExecution` : `assigned` | `in_progress` | `done` | `canceled` ; `execution_source` `template` | `assignment` ; template requis.
- `ChecklistTaskExecution` : `pending` | `done` | `skipped` | `observation_created`.
- Snapshots obligatoires à la création / matérialisation d'exécution.
- Pas d'endpoint `start` — passage `assigned` → `in_progress` au premier événement tâche.
- Handoff Observation depuis tâche (pipeline async existant).
- Exécutions checklist dans Execution Feed (`item_type: checklist`).
- **Profil → Gérer les checklists** : bibliothèque unique + gestion assignments sur les modèles (Owner/Director/Manager).
- **Feed Exécution `+`** : Action / Checklist (voir §5.16).
- Permission hints backend pour piloter l'UI ; backend enforce la sécurité.
- Pas de commentaires checklist en MVP.

**Migration DEV/test (Lots 2A–2B)** : suppression **destructive** de toutes les données `personal` legacy (`checklist_type = personal`) — pas de conversion, pas de préservation pilot. Environnement DEV/test uniquement.

Current code truth :

- Backend: [`apps/api/houston/checklists/`](../../../apps/api/houston/checklists/)
- OpenAPI: [`apps/api/schema.yml`](../../../apps/api/schema.yml)
- Frontend bibliothèque : [`apps/web/src/features/checklists/`](../../../apps/web/src/features/checklists/) — routes `/checklists`, `/checklists/new`, `/checklists/{id}`
- Feed card : [`execution-checklist-card.tsx`](../../../apps/web/src/features/execution/components/execution-checklist-card.tsx) — `execution_source`

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

### 5.4 Modèle cible (Lot 0)

```txt
ChecklistTemplate                    # checklist enregistrée uniquement
  establishment_id
  created_by
  business_unit                      # required
  title, description
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
  checklist_template_id              # required
  checklist_assignment_id            # nullable (template only)
  execution_source = template | assignment
  establishment_id
  assigned_to, assigned_by
  business_unit                      # required (snapshot)
  occurrence_date                    # nullable; idempotence assignment
  start_at, end_at, visible_from     # snapshots
  template_title, template_description
  status, last_activity_at
```

**Champs supprimés (cible)** : `checklist_type` sur template et execution ; `badge` sur template ; `execution_source = flash_todo`.

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

**Executions `template`** :

- `visible_from = null` (immédiat)
- `start_at` nullable sauf si défini à la création

**POST `checklist-templates/{id}/schedule/` (planification unifiée — page détail)** :

- Endpoint unique pour le bloc « Planification » sur le détail modèle.
- `start_date` optionnel : défaut = **date calendaire locale de l'établissement** (`establishment_local_date`), pas la date UTC serveur.
- Branche **ponctuelle** : `recurrence_days` absent, null ou `[]` → crée une `ChecklistExecution` (`execution_source = template`) ; réponse `result_type = execution`.
- Branche **récurrente** : `recurrence_days` non vide → crée une `ChecklistAssignment` ; réponse `result_type = assignment`.
- **Side effect récurrent** : à la création d'assignment, matérialisation eager de la 1ère occurrence (§5.7). Une `ChecklistExecution` peut exister en DB **sans** être retournée dans la réponse `/schedule/` (`execution: null` dans le JSON).
- CTA frontend (UX only ; backend enforce RBAC) : ponctuel → « Exécution » ; récurrent → « Créer l'affectation ».
- Les endpoints `POST .../executions/` et `POST .../assignments/` restent valides pour les autres flows (création composite, etc.).

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

- Plusieurs exécutions actives par template (assignments / lancements ponctuels distincts).
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
| `template` | **Assigné** ; Owner/Director (établissement) ; Manager si `business_unit` dans scope |
| `assignment` | Idem (exécution matérialisée) |

**Staff** : peut cancel si **assigné** ; ne peut pas cancel l'exécution d'un **tiers**.

### 5.13 Snapshots (conservé)

À la création d'exécution (template ou matérialisation) :

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

**Profil → Gérer les checklists** :

| Rôle | Accès |
| --- | --- |
| Owner / Director / Manager | Bibliothèque complète selon scope ; CRUD processus ; gestion assignments |
| Staff | Bibliothèque en **lecture seule** ; lancer exécution pour soi depuis un modèle accessible (« Lancer pour moi ») |

**Nav Profil « Listes » (MVP UX contract):** visible for **active Owner / Director / Manager / Staff memberships** in the selected establishment (`canShowChecklistsNav` is role-based on the active membership, not gated on `can_create_checklist_template`). **Active Staff** see the bibliothèque hub in **read-only** mode; create/edit/delete/assignment actions are hint-gated and API-enforced. Intentional — Staff needs scoped catalogue visibility for « Lancer pour moi ».

- Filtres bibliothèque : pôle, créées par moi
- Détail modèle : tâches, assignments planifiés (si autorisé), utiliser / assigner selon RBAC

**Feed Exécution `+`** (mobile-first) :

| Entrée | Comportement |
| --- | --- |
| **Action** | Inchangé (Owner/Director/Manager) |
| **Checklist** | Owner/Director/Manager : **Créer une checklist** / **Utiliser une checklist existante** (pour soi ou autrui). Staff : **Utiliser une checklist existante** — **Lancer pour moi** uniquement |

**Créer une checklist enregistrée** (Owner/Director/Manager — depuis `+` ou bibliothèque) :

- Titre, description optionnelle, tâches (≥1), BU
- Assigner maintenant : oui/non ; si oui : assigné + `end_at` optionnel
- `POST .../checklist-templates/` transactionnel (`assign_now` crée aussi exécution)

**Utiliser une checklist existante** :

- Choisir modèle accessible, assigné, `end_at` optionnel
- Staff : assigné forcé à soi-même
- `POST .../checklist-templates/{id}/executions/`

## 6. Hors MVP

- Endpoint `start` pour executions
- Statuts `draft`, `archived`, `completed`, `open` pour exécutions
- Flash To-do et endpoint `flash-todo/`
- Badge Process/To-do et filtre badge
- Modèle ou domaine `PersonalChecklist` / distinction shared/personal
- Deux bibliothèques ou permissions selon type de checklist
- Approbation modèles, marketplace, commentaires checklist, preuve photo obligatoire
- Validation manager à la complétion
- RRULE avancé, notifications checklist (Phase 6+)
- Historique UI des exécutions terminées (accès par ID seulement aujourd'hui)

**Operational realtime (implemented — not hors MVP):** checklist template/assignment and execution surfaces refresh via establishment-scoped WebSocket **invalidation** (`checklist.updated`, `execution.created`, `execution.updated`) emitted from `checklists/services.py` and `materialization.py`. Invalidation/refetch only — Checklist does not own realtime transport. Authoritative contract: [`realtime_domain.md`](realtime_domain.md). Catalogue entries: [`event_catalogue_v0.1.md`](../event_catalogue_v0.1.md).

## 7. Core Invariants

- Une checklist = un `ChecklistTemplate` enregistré ; pas d'exécution sans modèle.
- Bibliothèque = templates enregistrés uniquement.
- Recurrence vit sur `ChecklistAssignment`, pas sur `ChecklistExecution`.
- Backend owns all lifecycle transitions via explicit service methods.
- Single-assignee per execution et per assignment.
- `end_at` ne retire pas du feed actif — seuls `done` / `canceled`.
- Establishment scoping mandatory.
- No raw Observation text on checklist surfaces.
- Permission hints pilotent l'UI ; le backend est l'autorité de sécurité.

## 8. Main Objects (cible Lot 0)

Voir §5.4. Inspect [`models.py`](../../../apps/api/houston/checklists/models.py) before claiming field names match production code during migration.

## 9. Permissions

Establishment-scoped, backend-enforced. Helpers: [`permissions.py`](../../../apps/api/houston/checklists/permissions.py). UX hints: [`permission_hints.py`](../../../apps/api/houston/checklists/permission_hints.py) — **not authorization authority**.

### 9.1 Matrice cible (Lot 0)

| Capability | Owner / Director | Manager | Staff |
| --- | --- | --- | --- |
| Profil — Bibliothèque de checklists | yes | yes | yes (lecture) |
| Créer checklist enregistrée | yes (all BU) | yes, scoped BU | **no** |
| Voir bibliothèque (modèles accessibles) | all establishment | scoped BU | scoped BU |
| Modifier checklist enregistrée | all | scoped BU | **no** |
| Supprimer checklist enregistrée | all | scoped BU | **no** |
| Lancer exécution depuis modèle — pour soi | yes | yes, scoped BU | yes, scoped BU (**Lancer pour moi**) |
| Lancer exécution depuis modèle — pour autrui | yes (all BU) | yes, scoped BU | **no** |
| Gérer assignments (créer / PATCH / deactivate) | yes | scoped BU | **no** |
| Exécuter tâches (assigné) | if assignee | if assignee | if assignee |
| Annuler exécution | yes ; Manager scoped | scoped BU ; assigné | **assigné only** |
| Feed `+` — Action | yes | yes | no |
| Feed `+` — Checklist | yes | yes | yes (**Lancer pour moi** uniquement) |

**Assigné** :

- Owner/Director : tout membre actif de l'établissement
- Manager/Staff : membre actif couvrant le `business_unit` de la checklist (`MembershipScope`)

### 9.2 Permission hints (cible)

Les hints pilotent l'affichage des boutons et actions UI. Le backend rejette toute commande non autorisée (`403`).

| Resource | Hint keys (cible) |
| --- | --- |
| Template | `can_update`, `can_manage_tasks`, `can_activate`, `can_deactivate`, `can_delete`, `can_create_assignment`, `can_launch_execution`, `can_launch_execution_for_others` |
| Assignment | `can_update`, `can_deactivate` |
| Execution | `can_execute_tasks`, `can_cancel` |

Legacy hints supprimés : `can_create_personal_execution` ; tout hint lié à Flash To-do ou badge.

RBAC reference: [`rbac_permissions_domain.md`](rbac_permissions_domain.md).

## 10. API Surface

Inspect [`apps/api/schema.yml`](../../../apps/api/schema.yml) before claiming endpoints exist.

### 10.1 Endpoints cibles (Lot 0)

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `checklist-templates/` | Bibliothèque (filtres `business_unit_id`, `created_by_me`) / création enregistrée composite |
| GET, PATCH, DELETE | `checklist-templates/{id}/` | Detail / update / delete |
| POST | `checklist-templates/{id}/executions/` | Lancer exécution depuis modèle |
| POST | `checklist-templates/{id}/schedule/` | Planifier depuis détail modèle (ponctuel ou récurrent) |
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
  "tasks": [{ "title": "Fermer caisse" }],
  "assign_now": true,
  "assigned_to": "uuid",
  "end_at": "2026-06-09T23:00:00+02:00"
}
```

### 10.2 Endpoints legacy (supprimés)

| Endpoint | Statut |
| --- | --- |
| `GET/POST checklist-templates/?type=shared\|personal` | **Supprimé** |
| `POST .../personal-executions/` | **Supprimé** |
| `POST .../checklist-executions/flash-todo/` | **Supprimé** (Flash To-do retiré du produit) |

Aucun comportement actif ne dépend de ces endpoints.

### 10.3 POST `checklist-templates/{id}/schedule/` (réponse)

```json
{
  "result_type": "execution | assignment",
  "execution": { "...ChecklistExecutionDetail..." } | null,
  "assignment": { "...ChecklistAssignment..." } | null
}
```

- Branche ponctuelle : `result_type = execution`, `assignment = null`.
- Branche récurrente : `result_type = assignment`, `execution = null` dans la réponse **même si** une exécution est matérialisée en DB pour la 1ère occurrence (§5.7).

Execution Feed : `GET execution-feed/` — `item_type: action | checklist`.

## 11. Frontend Expectations (cible)

- **Bibliothèque unique** ; pas de sections personal/shared ; pas de badge Process/To-do
- **Feed `+`** : Action / Checklist
- Staff : pas de création processus ; « Lancer pour moi » depuis modèle existant
- Feed card : titre, progression, `execution_source` — pas de label Flash To-do ni badge Process/To-do
- TanStack Query + client OpenAPI généré
- Permission hints backend pour boutons modifier/supprimer/utiliser/lancer
- Lifecycle via commandes backend uniquement

## 12. Execution Feed integration

- Polymorphism `item_type: checklist`
- Feed item expose : title, progress, `execution_source`, `end_at`, `is_overdue`, BU label, status
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
- Exécutions existantes : `execution_source = assignment` ou `template` selon présence d'assignment
- Données Flash To-do legacy : à purger en DEV/test lors de la fermeture Lot 0

## 15. AI Agent Notes

- Do not use `checklist_type` shared/personal as product truth.
- Do not use `badge`, Flash To-do, or `execution_source = flash_todo` as product truth.
- Do not create separate Process/To-do models or endpoints.
- Every execution must reference a `ChecklistTemplate`.
- Staff cannot CRUD templates or create assignments — only « Lancer pour moi ».
- Keep `ChecklistAssignment` + materialization unless explicitly removed in a future lot.
- `/schedule/` branches on `recurrence_days`: empty → template execution ; non-empty → assignment (+ eager first occurrence materialization, not in schedule response).
- Do not assume `execution: null` in schedule response means no execution row exists for recurring schedules.
- Inspect `schema.yml` before claiming API shape.
- When changing APIs: update permissions, OpenAPI, generated clients, tests, and this document together.
- Archive [`houston_checklist_domain.md`](../../archive/codex/houston_checklist_domain.md) is historical only.
