# Houston — Feed / Query / Sorting Contract

**Version:** v0.1  
**Date:** 2026-05-24  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Signal Feed, Execution Feed, Notification Center, query, filters, sorting, pagination, realtime refetch  
**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(18).txt`

**Documents liés :**
- `Houston_rbac_permissions_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`
- `Houston_notification_matrix.md`
- `Houston_realtime_architecture.md`
- `Houston_event_catalog.md`

---

# 1. Objectif du document

Ce document formalise le **Feed / Query / Sorting Contract** de Houston.

Il définit :
- les feeds MVP ;
- les modes de vue ;
- les règles de visibilité ;
- les règles de query backend ;
- les filtres ;
- le tri ;
- la pagination ;
- les compteurs ;
- les items normalisés ;
- les endpoints ;
- l’intégration realtime ;
- les tests fonctionnels attendus.

---

# 2. Principe central

```txt
Feeds are authorized backend queries.
Realtime invalidates them.
Frontend never receives more than user is allowed to see.
```

---

# 3. Rôle du Feed Contract

```txt
Feed Contract = contrat backend/frontend des vues opérationnelles :
- visibilité
- queries
- tri
- filtres
- pagination
- compteurs
- refetch realtime
```

Le Feed Contract assemble :
- RBAC ;
- Signal Domain ;
- Action Domain ;
- Checklist Domain ;
- Notification Matrix ;
- Realtime Architecture ;
- API Contract.

---

# 4. Feeds MVP

## 4.1 Liste

```txt
MVP feeds:
├── Signal Feed
├── Execution Feed
└── Notification Center
```

## 4.2 Signal Feed

```txt
Signal Feed contains Signals only.
No raw Observations.
No Actions as primary items.
```

## 4.3 Execution Feed

```txt
Execution Feed contains:
├── Actions
├── Shared Checklist Executions
└── Personal Checklist Executions
```

## 4.4 Notification Center

```txt
Notification Center = feed dédié aux notifications in_app.
```

## 4.5 Source of truth

```txt
Feed API = source of truth.
Realtime only invalidates/refetches.
```

---

# 5. View modes

## 5.1 Modes validés

```txt
Feed view modes:
├── personal
└── general
```

## 5.2 Default

```txt
Default view_mode = personal.
User can switch to general if authorized.
```

## 5.3 Owner / Director

```txt
Owner/Director:
- default can be general
- access to all establishment feed items
```

---

# 6. Signal Feed visibility

## 6.1 Staff — personal

```txt
Staff Signal Feed personal =
Signals whose detected_domains intersect staff operational_domains.
```

## 6.2 Staff — general

```txt
Staff Signal Feed general =
all establishment Signals visible by product policy.
```

## 6.3 Manager — personal

```txt
Manager Signal Feed personal =
Signals whose detected_domains intersect manager operational_domains.
```

## 6.4 Manager — general

```txt
Manager Signal Feed general =
all establishment Signals.
```

## 6.5 General view ≠ action permission

```txt
General view visibility ≠ action permission.
Manager can act only if Signal.detected_domains intersects manager operational_domains.
```

## 6.6 Owner / Director

```txt
Owner/Director Signal Feed =
all establishment Signals.
```

---

# 7. Signal Feed statuses

## 7.1 Archived

```txt
Default Signal Feed excludes archived.
Archived accessible via explicit filter/search.
```

## 7.2 Default active statuses

```txt
Default active Signal Feed:
├── open
├── in_progress
├── resolved
└── canceled

Archived excluded by default.
```

## 7.3 Point à challenger

```txt
resolved/canceled doivent peut-être disparaître après délai court.
```

Pour MVP :
- ils restent dans les statuses par défaut ;
- ils peuvent être poussés plus bas dans le tri ;
- archived reste hors feed actif.

---

# 8. Signal Feed sorting

## 8.1 Ordre principal

```txt
Signal Feed order:
1. pinned
2. high urgency
3. open
4. in_progress
5. resolved
6. canceled
then recent activity desc
```

## 8.2 Pinned

```txt
Pinned appears before high urgency.
Pinned only allowed on open Signals.
```

## 8.3 Tri secondaire

```txt
Secondary sort = last_activity_at desc.
```

## 8.4 last_activity_at

```txt
Signal.last_activity_at maintained by events/services.
```

`last_activity_at` doit être mis à jour par les services/events lors de :
- SignalCreated ;
- SignalAggregated ;
- SignalCommentAdded ;
- ActionCreated ;
- ActionStatusChanged ;
- SignalDomainAdded/Removed ;
- SignalUrgencyChanged ;
- SignalPinned/Unpinned.

---

# 9. Signal Feed item

## 9.1 Champs validés

```txt
SignalFeedItem:
- id
- title
- structured_summary_short
- status
- urgency
- pinned
- detected_domains
- operational_unit
- location_text
- candidate_signal_count
- media_count
- actions_count
- comments_count
- last_activity_at
- created_at
```

## 9.2 candidate_signal_count

```txt
Signal Feed item shows candidate_signal_count.
```

## 9.3 detected_domains

```txt
Signal Feed item shows detected_domains badges, ordered by confidence desc.
```

## 9.4 confidence_score

```txt
Do not show confidence_score in normal feed MVP.
Use it for ordering/debug/analytics only.
```

---

# 10. Signal Feed filters

## 10.1 Filtres MVP

```txt
Signal Feed filters MVP:
├── view_mode
├── domain
├── status
├── urgency
└── search
```

## 10.2 operational_unit

`operational_unit` n’est pas retenu dans les filtres MVP du fichier d’arbitrage.

Il peut être ajouté post-MVP si le volume terrain le justifie.

## 10.3 Domain filter

```txt
Domain filter supports multi-select.
Match if item domains intersect selected domains.
```

## 10.4 Status filter

```txt
Status filter supports multi-select.
```

## 10.5 view_mode + filters

```txt
view_mode combines with filters.
RBAC always applies first.
```

---

# 11. Signal Search

## 11.1 Champs recherchables

```txt
Signal search fields:
- title
- structured_summary
- location_text
- runtime_tags
- operational_unit label
No raw Observation text.
```

## 11.2 Comments search

Decision :

```txt
No comments search MVP.
```

---

# 12. Execution Feed visibility

## 12.1 Staff — personal

```txt
Staff Execution Feed personal =
├── assigned Actions
├── assigned Shared Checklist Executions
└── own Personal Checklist Executions
```

## 12.2 Staff — general

```txt
Staff Execution Feed general = not MVP.
Staff execution remains personal.
```

## 12.3 Manager — personal

```txt
Manager Execution Feed personal =
├── Actions created by manager
├── Actions in manager operational_domains
├── Shared Checklist Executions assigned by manager
├── Shared Checklist Executions assigned to manager
└── own Personal Checklist Executions
```

## 12.4 Manager — general

```txt
Manager Execution Feed general =
Actions + Shared Checklist Executions whose domains intersect manager operational_domains.
+ own Personal Checklist
```

## 12.5 Owner / Director

```txt
Owner/Director Execution Feed =
├── all establishment Actions
├── all Shared Checklist Executions
└── own Personal Checklist Executions
```

---

# 13. Checklist visibility in feeds

## 13.1 Personal Checklist

```txt
Personal Checklist items visible only to creator.
```

## 13.2 Shared Checklist Execution

```txt
Shared Checklist Execution visibility:
- assignee sees assigned execution
- assigned_by sees execution
- Manager sees executions in operational_domains
- Owner/Director see all
```

---

# 14. Execution Feed item model

## 14.1 Normalized union

```txt
Execution Feed API returns normalized union:
item_type = action | shared_checklist_execution | personal_checklist_execution
```

## 14.2 No feed_items table MVP

```txt
No feed_items table MVP.
Use query services + normalized response.
```

## 14.3 Why no feed_items table MVP

Évite :
- duplication d’état ;
- sync complexe ;
- bug entre source métier et feed ;
- sur-ingénierie avant preuve terrain.

---

# 15. Execution Feed sorting

## 15.1 Ordre validé

```txt
Execution Feed order:
1. overdue
2. pending_validation requiring user action
3. assigned/open not accepted
4. in_progress/reopened
5. assigned checklists not started
6. completed/done/canceled lower
then due_at asc nulls last
then updated_at desc
```

## 15.2 requires_current_user_action

```txt
Execution Feed item includes requires_current_user_action boolean.
```

## 15.3 Meaning

`requires_current_user_action = true` quand l’utilisateur courant doit agir maintenant.

Exemples :
- Action assignée à lui et pas encore acceptée ;
- Action à valider par lui ;
- Checklist assignée à lui et pas encore démarrée ;
- Action reopened assignée à lui.

---

# 16. Execution Feed statuses

## 16.1 Action statuses listed

```txt
Execution Feed default statuses:
├── open
├── in_progress
├── pending_validation
├── reopened
├── done
└── canceled
```

## 16.2 ChecklistExecution statuses

```txt
ChecklistExecution Feed statuses:
assigned, in_progress, completed, canceled
```

## 16.3 Default focus

```txt
Default Execution Feed focuses active items.
Completed/done/canceled accessible via status filter.
```

## 16.4 Active default

```txt
Active Execution Feed default:
Actions: open, in_progress, pending_validation, reopened
ChecklistExecutions: assigned, in_progress
PersonalChecklists: active/in_progress
```

---

# 17. Execution Feed filters

## 17.1 Mine filters

```txt
Execution Feed filters:
- assigned_to_me
- created_by_me
- requires_my_action
```

## 17.2 Filters MVP

```txt
Execution Feed filters MVP:
├── item_type
├── status
├── domain
├── requires_my_action
└── search
```

## 17.3 Filters not MVP

Non retenus MVP :
- due_at ;
- assignee.

Ils peuvent être ajoutés post-MVP.

---

# 18. Execution Search

## 18.1 Champs recherchables

```txt
Execution search fields:
- Action title/description
- linked Signal title/summary
- Checklist title
- Checklist task labels
No raw Observation text.
```

## 18.2 Comments search

Pas MVP.

---

# 19. Pagination

## 19.1 Type

```txt
Use cursor-based pagination for feeds.
```

## 19.2 Page size

```txt
Default page_size = 25.
Max page_size = 50.
```

## 19.3 Cursor

```txt
cursor = encoded(sort_bucket, sort_timestamp, id)
```

## 19.4 Pourquoi cursor-based

Les feeds changent souvent avec le realtime.  
Offset pagination serait instable.

---

# 20. Feed API endpoints

## 20.1 Endpoints validés

```txt
GET /api/v1/establishments/:id/signal_feed
GET /api/v1/establishments/:id/execution_feed
GET /api/v1/establishments/:id/notifications
```

## 20.2 Query params recommandés

Signal Feed :

```txt
view_mode
domains[]
statuses[]
urgency
search
cursor
page_size
```

Execution Feed :

```txt
view_mode
item_types[]
statuses[]
domains[]
requires_my_action
search
cursor
page_size
```

Notifications :

```txt
status
cursor
page_size
```

---

# 21. Feed response standard

## 21.1 Format

```json
{
  "items": [],
  "next_cursor": "string|null",
  "has_more": true,
  "applied_filters": {},
  "counts": {}
}
```

## 21.2 applied_filters

Le backend retourne les filtres réellement appliqués.

Objectifs :
- debug frontend ;
- clarté UX ;
- éviter ambiguïtés sur filtres invalides ou non autorisés.

---

# 22. ExecutionFeedItem fields

## 22.1 Champs validés

```txt
ExecutionFeedItem:
- item_type
- item_id
- title
- status
- priority
- due_at
- overdue
- assignee
- created_by / assigned_by
- related_signal_id optional
- related_signal_title optional
- domains
- requires_current_user_action
- last_activity_at
```

## 22.2 priority

Pour Action :
- dérivée de Signal urgency selon arbitrages précédents.

Pour Checklist :
- normal par défaut MVP.

---

# 23. Counts

## 23.1 Counts optionnels MVP

```txt
Counts optional MVP:
- total_active
- open/in_progress/pending_validation
- overdue
- unread_notifications
```

## 23.2 Counts exacts MVP

```txt
MVP counts exact for pilot volumes.
Optimize/cache if needed.
```

## 23.3 Performance

Si volumes augmentent :
- cache counts ;
- matérialisation partielle ;
- async counters ;
- pagination optimisée.

---

# 24. Query pipeline

## 24.1 Ordre validé

```txt
Query pipeline:
1. RBAC scope
2. view_mode scope
3. filters
4. sort
5. pagination
```

## 24.2 Pourquoi

RBAC avant tout.

Cela évite :
- fuite par counts ;
- fuite par filtres ;
- fuite par search ;
- incohérence avec realtime.

---

# 25. Realtime refetch

## 25.1 Strategy

```txt
On realtime feed event:
- invalidate current query key
- refetch first page with current filters
- optionally refetch detail if open
```

## 25.2 No local patching by default

Le frontend ne doit pas reconstruire les règles de feed.

Realtime payload = signal d’invalidation.

---

# 26. Backend query services

## 26.1 SignalFeed::Query

Responsabilités :
- appliquer RBAC ;
- appliquer view_mode ;
- appliquer filters ;
- appliquer sort ;
- appliquer pagination ;
- construire SignalFeedItem.

## 26.2 ExecutionFeed::Query

Responsabilités :
- construire scopes Actions ;
- construire scopes Shared Checklist Executions ;
- construire scopes Personal Checklist Executions ;
- appliquer visibility ;
- fusionner items ;
- trier ;
- paginer ;
- normaliser ExecutionFeedItem.

## 26.3 Notifications::Query

Responsabilités :
- lister notifications du recipient ;
- appliquer status ;
- trier par created_at desc ;
- paginer ;
- retourner unread_count si utile.

## 26.4 Feed::Cursor

Responsabilités :
- encoder cursor ;
- décoder cursor ;
- valider sort_bucket/sort_timestamp/id ;
- éviter cursor tampering.

---

# 27. Indexes recommandés

## 27.1 Signals

```txt
signals:
- establishment_id
- status
- urgency
- pinned
- last_activity_at
- created_at
```

Domains étant multi-valués, prévoir une stratégie adaptée :
- table join `signal_detected_domains` ;
- index sur `domain_key` / `establishment_id` ;
- ou JSONB index si choix JSONB.

Recommandation build :
```txt
Use join table for detected_domains if query/filter domain is central.
```

## 27.2 Actions

```txt
actions:
- establishment_id
- assigned_to_id
- created_by_id
- status
- due_at
- updated_at
- signal_id
```

Domain filtering Action via Signal domains ou champ snapshot domain selon architecture finale.

## 27.3 ChecklistExecutions

```txt
checklist_executions:
- establishment_id
- assignee_id
- assigned_by_id
- status
- updated_at
```

## 27.4 Notifications

```txt
notifications:
- establishment_id
- recipient_id
- status
- created_at
```

---

# 28. Tests fonctionnels MVP

## 28.1 RBAC first

```txt
Given user has no access to a Signal
When user queries Signal Feed
Then Signal never appears
And counts do not include it
```

## 28.2 Staff personal Signal Feed

```txt
Given Staff has operational_domain housekeeping
And Signal has detected_domain housekeeping
When Staff queries Signal Feed personal
Then Signal appears
```

## 28.3 Staff general Signal Feed

```txt
Given Staff switches to general
When querying Signal Feed
Then all establishment Signals visible by product policy appear
```

## 28.4 Manager general cannot act on all

```txt
Given Manager sees Signal in general view
And Signal has no matching manager domain
Then Signal appears read/comment-only
And action creation is not allowed
```

## 28.5 Archived excluded

```txt
Given archived Signal
When default Signal Feed is queried
Then Signal does not appear
```

## 28.6 Signal sorting

```txt
Given pinned, high urgency, open, in_progress Signals
When Signal Feed is queried
Then order is pinned first, then high urgency, then status buckets
```

## 28.7 Execution Feed Staff

```txt
Given Staff has assigned Action and assigned ChecklistExecution
When querying Execution Feed personal
Then both appear
And unassigned domain items do not appear
```

## 28.8 Personal Checklist private

```txt
Given User A has Personal Checklist
When User B queries Execution Feed
Then User A Personal Checklist does not appear
```

## 28.9 Cursor pagination

```txt
Given more than 25 feed items
When first page is queried
Then next_cursor is returned
And next page uses cursor without duplicates
```

## 28.10 Realtime refetch

```txt
Given frontend receives SignalCreated realtime payload
When current Signal Feed query is active
Then frontend invalidates query key
And refetches first page with current filters
```

---

# 29. Décisions validées — index

| Décision | Statut |
|---|---:|
| Feed Contract = backend/frontend operational view contract | Validé |
| MVP feeds = Signal Feed / Execution Feed / Notification Center | Validé |
| Signal Feed contains Signals only | Validé |
| No raw Observations in Signal Feed | Validé |
| No Actions as primary Signal Feed items | Validé |
| Execution Feed contains Actions + Shared Checklist Executions + Personal Checklist Executions | Validé |
| Notification Center is dedicated in-app notification feed | Validé |
| Feed API source of truth | Validé |
| Realtime only invalidates/refetches | Validé |
| view modes personal/general | Validé |
| default view_mode personal | Validé |
| Owner/Director default can be general | Validé |
| Staff Signal personal by operational_domains | Validé |
| Staff Signal general all visible establishment Signals | Validé |
| Manager Signal personal by operational_domains | Validé |
| Manager Signal general all establishment Signals | Validé |
| General visibility ≠ action permission | Validé |
| Owner/Director Signal Feed all Signals | Validé |
| Archived excluded by default | Validé |
| Default Signal statuses open/in_progress/resolved/canceled | Validé |
| Signal order pinned > high urgency > statuses > recent | Validé |
| Pinned before high urgency | Validé |
| Pinned only open Signals | Validé |
| Secondary sort last_activity_at desc | Validé |
| Signal.last_activity_at maintained by events/services | Validé |
| candidate_signal_count shown | Validé |
| detected_domains badges shown ordered by confidence desc | Validé |
| confidence_score hidden in normal feed | Validé |
| Signal filters view_mode/domain/status/urgency/search | Validé |
| operational_unit filter not MVP | Validé |
| No comments search MVP | Validé |
| Staff Execution personal validé | Validé |
| Staff Execution general not MVP | Validé |
| Manager Execution personal validé | Validé |
| Manager Execution general domains + own Personal Checklist | Validé |
| Owner/Director Execution all establishment Actions/Shared + own Personal | Validé |
| Personal Checklists visible only to creator | Validé |
| Shared Checklist visibility rules validées | Validé |
| Execution normalized union response | Validé |
| No feed_items table MVP | Validé |
| Execution sorting validé | Validé |
| requires_current_user_action included | Validé |
| Active Execution default focuses active items | Validé |
| completed/done/canceled via status filter | Validé |
| Execution filters item_type/status/domain/requires_my_action/search | Validé |
| due_at and assignee filters not MVP | Validé |
| Execution search without raw Observation | Validé |
| Cursor pagination | Validé |
| page_size 25 / max 50 | Validé |
| cursor encoded(sort_bucket, sort_timestamp, id) | Validé |
| Dedicated feed endpoints | Validé |
| Standard response items/next_cursor/has_more/applied_filters/counts | Validé |
| SignalFeedItem fields validés | Validé |
| ExecutionFeedItem fields validés | Validé |
| Counts optional MVP | Validé |
| Counts exact MVP pilot | Validé |
| Domain filter multi-select | Validé |
| Status filter multi-select | Validé |
| view_mode combines with filters | Validé |
| Query pipeline RBAC → view_mode → filters → sort → pagination | Validé |
| Realtime refetch current query key | Validé |
| Final principle validé | Validé |

---

# 30. Points à traiter ailleurs

## 30.1 Technical Architecture / ERD

À intégrer :
- detected_domains model ;
- last_activity_at ;
- indexes feed ;
- query services ;
- cursor utility ;
- normalized response serializers.

## 30.2 API Contract

À détailler :
- exact query params ;
- response schemas ;
- error codes ;
- cursor encoding ;
- filter validation.

## 30.3 Realtime Architecture

Déjà cadré :
- realtime invalidates feed queries ;
- no object snapshot ;
- feed_target optionnel ;
- no changed_fields MVP.

## 30.4 Frontend

À cadrer :
- query keys ;
- filter UI ;
- infinite scroll ;
- empty states ;
- loading states ;
- realtime refetch UX.

---

# 31. Recommandation finale

Le Feed / Query / Sorting Contract est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Feeds are authorized backend queries.
Realtime invalidates them.
Frontend never receives more than user is allowed to see.
```

Le build doit maintenant s’appuyer sur :
- endpoints dédiés ;
- query services backend ;
- RBAC-first query pipeline ;
- cursor pagination ;
- normalized Execution Feed union ;
- `Signal.last_activity_at` ;
- no feed_items table MVP ;
- filters limités MVP ;
- realtime query invalidation.
