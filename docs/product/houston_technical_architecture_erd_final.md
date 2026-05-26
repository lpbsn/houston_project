# Houston — Technical Architecture / ERD Final

**Version:** v0.1  
**Date:** 2026-05-26  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — architecture technique, stack, monolithe modulaire, apps Django, ERD logique, tables, relations, services, jobs, indexes, tests

**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(19).txt`

**Documents liés :**
- `Houston_authentication_identity_domain.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_onboarding_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`
- `Houston_ai_overview.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_ai_transcription_contract.md`
- `Houston_ai_onboarding_contract.md`
- `Houston_event_catalog.md`
- `Houston_notification_matrix.md`
- `Houston_upload_media_lifecycle.md`
- `Houston_security_rgpd_baseline.md`
- `Houston_realtime_architecture.md`
- `Houston_feed_query_sorting_contract.md`

---

# 1. Objectif du document

Ce document consolide l’architecture technique finale du MVP Houston.

Il définit :
- le stack technique cible ;
- la structure backend Django ;
- les apps/modules ;
- l’ERD logique ;
- les tables principales ;
- les relations ;
- les patterns de services ;
- les jobs async ;
- les events ;
- les permissions ;
- les indexes ;
- les conventions API ;
- les choix de tests ;
- les choix d’outillage ;
- les points à challenger avant build.

Ce document sert de base au futur :
- `Houston_api_contract_mvp.md` ;
- backlog technique ;
- génération des migrations ;
- implémentation Cursor/Codex/Claude Code ;
- build MVP.

---

# 2. Décision centrale

```txt
Houston MVP = modular monolith Django.
One deployable backend.
Domain boundaries by Django apps/modules.
```

Le backend reste un seul système déployable.

Les domaines sont séparés par apps Django et modules internes, mais ne deviennent pas des microservices.

---

# 3. Stack technique retenu

## 3.1 Backend

```txt
Python 3.13
Django
Django REST Framework
PostgreSQL
Celery
Redis
Django Channels
Pydantic
drf-spectacular
```

## 3.2 Frontend

```txt
Django Templates
HTMX
TypeScript ciblé via Vite
Alpine.js or Stimulus if needed
PWA manifest
Service worker minimal
Optional OpenAPI TypeScript client for JSON API consumers
```

## 3.3 Storage / infra locale

```txt
S3-compatible storage
MinIO local
Docker Compose local
```

## 3.4 Challenge stack

Django + DRF + Celery + Channels est cohérent pour Houston parce que :
- le produit est transactionnel ;
- les règles métier sont importantes ;
- PostgreSQL est central ;
- les feeds sont backend-authorized ;
- les jobs async sont nécessaires pour IA/events/uploads ;
- Django Admin donne un support technique rapide ;
- OpenAPI documente les endpoints JSON et prépare les futurs consommateurs API, notamment mobile ou modules TypeScript ciblés.

Point à surveiller :
- Django Channels + Celery + Redis ajoute de la complexité runtime.
- Il faudra garder le realtime minimal : invalidation/refetch, pas transport complet de données.
- Le monolithe doit rester modulaire, pas devenir un `core` fourre-tout.

---

# 4. Structure projet cible

## 4.1 Structure validée

```txt
apps/api/
├── config/
└── Houston/
    ├── core/
    ├── accounts/
    ├── organizations/
    ├── establishments/
    ├── observations/
    ├── signals/
    ├── actions/
    ├── checklists/
    ├── comments/
    ├── notifications/
    ├── realtime/
    ├── ai/
    ├── events/
    └── uploads/
```

## 4.2 Renommages validés

```txt
ai_pipeline → ai
domain_events → events
```

## 4.3 Nommage

```txt
Use plural app names consistently:
accounts, organizations, establishments, observations, signals, actions...
```

## 4.4 `core`

```txt
core:
- BaseModel
- TimeStampedModel
- UUID utilities
- shared exceptions/result
Do not put business logic in core.
```

## 4.5 Éviter `common/`

```txt
Avoid common/ unless strictly necessary.
```

---

# 5. Architecture par couches

## 5.1 Règle générale

```txt
Views/serializers handle HTTP.
Services handle commands/write use-cases.
Selectors/queries handle read models.
Models hold persistence and simple invariants.
Events trigger async consumers.
```

## 5.2 Command side

Exemples :

```txt
signals/services.py
actions/services.py
observations/services.py
checklists/services.py
```

Responsabilités :
- validation métier ;
- transactions ;
- mutations DB ;
- émission events after commit ;
- mapping erreurs métier.

## 5.3 Query side

```txt
Use query/selectors modules for feed/read models.
Use services for commands/write use-cases.
```

Exemples :
- `signals/selectors.py`
- `actions/selectors.py`
- `feeds/signal_feed.py` si app dédiée plus tard ;
- `checklists/selectors.py`.

## 5.4 Permissions

```txt
Use domain permission services:
permissions/can.py or establishments/permissions.py
```

Recommandation MVP :
- centraliser dans `Houston/establishments/permissions.py` ou `Houston/core/permissions.py` ;
- éviter les permissions dispersées dans les views.

---

# 6. Conventions globales de modèles

## 6.1 UUID

```txt
All domain models use UUID primary keys.
```

## 6.2 Timestamps

```txt
Every domain table:
- id UUID
- created_at
- updated_at
```

## 6.3 Soft delete

```txt
Soft delete only where product requires it:
- Observation admin-only
- ObservationMedia
- maybe User deleted/anonymized
- admin/support destructive actions
```

Ne pas généraliser `deleted_at` partout.

## 6.4 Multi-tenancy

```txt
All runtime tables include establishment_id.
No schema-per-tenant MVP.
```

## 6.5 Organization denormalization

```txt
Runtime domain tables: establishment_id.
Events/logs can include organization_id denormalized.
```

---

# 7. Organizations / Establishments

## 7.1 Relation principale

```txt
Organization
└── Establishments
    └── EstablishmentMemberships
```

## 7.2 Billing future

Décision utilisateur :

```txt
Billing future belongs to Establishment.
Operational runtime belongs to Establishment.
```

Point à challenger :
- si Houston vend à des groupes multi-sites plus tard, facturer au niveau `Organization` peut devenir plus logique.
- pour le MVP mono-pilote / établissement, facturer à `Establishment` est acceptable.

## 7.3 Organization

```txt
Organization
- id
- name
- status
- created_at
- updated_at
```

## 7.4 Establishment

```txt
Establishment
- id
- organization_id
- name
- activity_description
- status
- activated_at
- created_at
- updated_at
```

---

# 8. Accounts / Authentication

## 8.1 User global

```txt
User global.
Access through EstablishmentMembership.
```

## 8.2 User model

```txt
User
- id
- email nullable
- login_identifier nullable
- identity_type email|username
- password_hash
- status
- token_version
- email_verified_at
- last_login_at
- created_at
- updated_at
```

## 8.3 User identities

```txt
Email identity:
- required for Owner/Director/Manager

Username identity:
- allowed for Staff
- email optional
- managed by establishment managers
```

## 8.4 UserSession

```txt
UserSession
- id
- user_id
- status
- refresh_token_digest
- refresh_token_family_id
- user_agent
- ip_metadata
- last_used_at
- expires_at
- revoked_at
- created_at
- updated_at
```

## 8.5 Invitation

```txt
Invitation
- id
- establishment_id
- email nullable
- login_identifier nullable
- identity_type email|username
- role
- operational_domains
- invited_by_id
- token_digest
- status
- expires_at
- accepted_at
- created_at
- updated_at
```

---

# 9. EstablishmentMembership / RBAC

## 9.1 EstablishmentMembership

```txt
EstablishmentMembership
- id
- user_id
- establishment_id
- role
- status
- created_at
- updated_at
```

## 9.2 Membership domains

Décision :

```txt
membership_domains join table.
```

```txt
MembershipDomain
- id
- membership_id
- operational_domain_id
- created_at
- updated_at
```

## 9.3 Authorization

```txt
Authorization always reads current EstablishmentMembership from DB/cache.
JWT claims are identity/session only.
```

Ne pas utiliser les claims JWT comme autorité RBAC.

---

# 10. Onboarding / Establishment knowledge

## 10.1 OperationalDomain

```txt
OperationalDomain table scoped to Establishment.
domain_key stable.
label editable.
active flag.
```

```txt
OperationalDomain
- id
- establishment_id
- domain_key
- label
- active
- created_at
- updated_at
```

## 10.2 OperationalModule

Décision :

```txt
OperationalModule table
```

```txt
OperationalModule
- id
- key
- label
- active
- created_at
- updated_at
```

Pour activation par établissement :

```txt
EstablishmentOperationalModule
- id
- establishment_id
- operational_module_id
- active
- created_at
- updated_at
```

## 10.3 OperationalUnit

```txt
OperationalUnit
- id
- establishment_id
- key
- label
- active
- created_at
- updated_at
```

## 10.4 EstablishmentKnowledgeItem

```txt
EstablishmentKnowledgeItem
- id
- establishment_id
- item_type vocabulary|runtime_tag|routing_hint
- key
- value
- metadata
- active
- created_at
- updated_at
```

---

# 11. Observations

## 11.1 Observation

```txt
Observation
- id
- establishment_id
- author_id
- raw_text
- source direct|checklist
- checklist_execution_id nullable
- checklist_task_execution_id nullable
- operational_unit_id nullable
- submitted_at
- deleted_at nullable
- created_at
- updated_at
```

## 11.2 ObservationProcessing

```txt
ObservationProcessing
- id
- observation_id
- status queued|processing|retrying|processed|failed
- outcome signals_proposed|no_signal_created|invalid_input
- attempts
- last_error_code
- correlation_id
- started_at nullable
- processed_at nullable
- created_at
- updated_at
```

## 11.3 Outcome

```txt
ObservationProcessing.outcome enum.
```

## 11.4 ObservationMedia

```txt
ObservationMedia
- id
- observation_id
- establishment_id
- uploaded_by_id
- storage_key
- mime_type
- size
- width
- height
- position
- deleted_at
- created_at
- updated_at
```

---

# 12. Uploads

## 12.1 TemporaryUpload

```txt
TemporaryUpload
- id
- establishment_id
- user_id
- upload_type observation_photo|transcription_audio
- storage_key
- mime_type
- file_size_bytes
- status uploaded|linked|transcribing|deleted|expired|failed
- expires_at
- metadata
- created_at
- updated_at
```

## 12.2 Storage

```txt
S3-compatible storage in production.
MinIO locally.
Private files only.
Signed URLs generated after RBAC check.
```

---

# 13. Signals

## 13.1 Signal

```txt
Signal
- id
- establishment_id
- title
- structured_summary
- status open|in_progress|resolved|canceled|archived
- urgency normal|high
- pinned
- candidate_signal_count
- operational_unit_id nullable
- location_text nullable
- last_activity_at
- created_at
- updated_at
```

Note : `location_text` was present in previous domain contracts and should be kept even if omitted in the arbitration list.

## 13.2 SignalDetectedDomain

```txt
SignalDetectedDomain
- id
- signal_id
- operational_domain_id
- domain_key
- confidence_score
- added_by_id nullable
- added_by_type system|user|ai
- created_at
- updated_at
```

## 13.3 ObservationSignalLink

```txt
ObservationSignalLink
- id
- observation_id
- signal_id
- link_type created|aggregated
- candidate_signal_id nullable
- created_at
- updated_at
```

## 13.4 SignalCandidate

Décision arbitrée :

```txt
SignalCandidate optional table, retained 14 days or linked metadata.
Pour MVP, éviter une table et stocker output IA structuré 14 jours.
Mais pour analytics aggregation_hint accepted/rejected, table candidate est utile.
```

Décision MVP recommandée :

```txt
No durable SignalCandidate table MVP.
Use AIStructuredOutput retained 14 days.
Store accepted/rejected aggregation metrics in AI metrics/events.
```

À challenger si analytics pipeline devient prioritaire.

---

# 14. Actions

## 14.1 Action

```txt
Action
- id
- signal_id
- establishment_id
- title
- description
- status open|in_progress|pending_validation|done|canceled|reopened
- priority normal|high
- assigned_to_id
- created_by_id
- due_at nullable
- reopen_count
- created_at
- updated_at
```

## 14.2 Priority

```txt
Action.priority stored as normal/high but initialized from Signal urgency.
No independent user control MVP.
```

---

# 15. Checklists

## 15.1 Models

```txt
ChecklistTemplate
ChecklistTaskTemplate
ChecklistExecution
ChecklistTaskExecution
```

## 15.2 Shared / Personal

```txt
ChecklistTemplate.template_type = shared|personal
ChecklistExecution.execution_type = shared|personal
```

## 15.3 ChecklistTemplate

```txt
ChecklistTemplate
- id
- establishment_id nullable for personal if needed
- created_by_id
- template_type shared|personal
- title
- description
- status draft|active|archived
- created_at
- updated_at
```

## 15.4 ChecklistTaskTemplate

```txt
ChecklistTaskTemplate
- id
- checklist_template_id
- label
- description nullable
- position
- created_at
- updated_at
```

## 15.5 ChecklistExecution

```txt
ChecklistExecution
- id
- establishment_id
- checklist_template_id nullable
- execution_type shared|personal
- title_snapshot
- assigned_to_id
- assigned_by_id nullable
- status assigned|in_progress|completed|canceled
- started_at nullable
- completed_at nullable
- canceled_at nullable
- created_at
- updated_at
```

## 15.6 ChecklistTaskExecution

```txt
ChecklistTaskExecution
- id
- checklist_execution_id
- checklist_task_template_id nullable
- snapshot_label
- snapshot_description
- position
- status pending|done|skipped|observation_created
- completed_at nullable
- skipped_at nullable
- observation_id nullable
- created_at
- updated_at
```

## 15.7 Snapshot

```txt
ChecklistTaskExecution stores snapshot_label/snapshot_description/order.
```

## 15.8 Checklist domains

```txt
ChecklistTemplateDomain / ChecklistExecutionDomain join.
```

```txt
ChecklistTemplateDomain
- id
- checklist_template_id
- operational_domain_id
- created_at
- updated_at

ChecklistExecutionDomain
- id
- checklist_execution_id
- operational_domain_id
- created_at
- updated_at
```

---

# 16. Comments

## 16.1 Comment

```txt
Comment
- id
- establishment_id
- subject_type signal|action
- subject_id
- author_id
- body
- created_at
- updated_at
```

## 16.2 CommentMention

```txt
CommentMention
- id
- comment_id
- mentioned_user_id
- created_at
- updated_at
```

## 16.3 Comment visibility

- Signal comments are visible in linked Actions.
- Action comments are scoped to their Action.
- Realtime/comment payloads contain `comment_id`, not full body.

---

# 17. Notifications

## 17.1 Notification

```txt
Notification
- id
- establishment_id
- recipient_id
- source_event_id
- subject_type
- subject_id
- priority info|action_required|urgent|system
- title
- body
- status unread|read|archived
- read_at nullable
- archived_at nullable
- created_at
- updated_at
```

## 17.2 NotificationDelivery

```txt
NotificationDelivery
- id
- notification_id
- channel in_app|push|email
- status queued|sent|delivered|failed|skipped
- provider nullable
- provider_message_id nullable
- attempts
- last_error nullable
- delivered_at nullable
- created_at
- updated_at
```

---

# 18. Events

## 18.1 ApplicationEvent

```txt
ApplicationEvent
- id
- event_type
- event_version
- category business|technical|ai|audit|system
- organization_id nullable
- establishment_id nullable
- actor_id nullable
- actor_type nullable
- subject_type
- subject_id
- correlation_id
- causation_id nullable
- idempotency_key nullable
- payload
- occurred_at
- created_at
- updated_at
```

## 18.2 EventDelivery

```txt
EventDelivery
- id
- application_event_id
- consumer_name
- status queued|processing|processed|failed|skipped
- attempts
- last_error nullable
- processed_at nullable
- created_at
- updated_at
```

## 18.3 Dispatch pattern

```txt
Business transaction writes ApplicationEvent.
Celery dispatches consumers after commit.
```

---

# 19. AI

## 19.1 AIUsageLog

```txt
AIUsageLog
- id
- establishment_id
- ai_domain transcription|onboarding|observation_pipeline
- provider
- model
- prompt_version
- status
- latency_ms
- input_tokens nullable
- output_tokens nullable
- input_audio_duration_ms nullable
- input_audio_size_bytes nullable
- cost_estimate
- error_code nullable
- correlation_id
- created_at
- updated_at
```

## 19.2 AIStructuredOutput

```txt
AIStructuredOutput
- id
- ai_usage_log_id
- ai_domain
- output_json
- expires_at
- created_at
- updated_at
```

## 19.3 Retention

```txt
AIStructuredOutput retained 14 days.
No prompt/content logs in standard app logs.
```

---

# 20. Celery / Redis / Channels

## 20.1 Celery

```txt
Celery broker = Redis.
Task results disabled unless needed.
Business status stored in domain tables.
```

## 20.2 Redis sharing

```txt
MVP: same Redis instance acceptable.
Use separate DB indexes / prefixes for Celery, Channels, cache.
```

## 20.3 Channels

```txt
Django Channels for websocket.
channels_redis for production channel layer.
```

## 20.4 Broadcast flow

```txt
ApplicationEvent
→ EventDelivery
→ Celery consumer
→ RealtimeBroadcaster
→ Django Channels
```

---

# 21. Pydantic / DRF / OpenAPI

## 21.1 Pydantic

```txt
Use Pydantic for:
- AI structured input/output schemas
- domain service command DTOs if useful
- OpenAI response validation
```

## 21.2 DRF serializers

```txt
Use DRF serializers for API request/response.
```

## 21.3 OpenAPI

```txt
Use drf-spectacular for OpenAPI.
Generate optional TypeScript client for JSON API consumers.
Do not require generated TypeScript client for HTMX-rendered screens.
```

## 21.4 API style

```txt
REST-first API.
Use command endpoints for domain transitions:
POST /actions/:id/accept
POST /actions/:id/mark_done
POST /signals/:id/resolve
```

## 21.5 API versioning

```txt
Use URL versioning: /api/v1/
```

## 21.6 Error response

```json
{
  "error": {
    "code": "ACTION_NOT_ALLOWED",
    "message": "Human readable message",
    "details": {}
  }
}
```

---

# 22. Transactions / Events

## 22.1 transaction.atomic

```txt
Use transaction.atomic in domain services.
Publish events after commit.
```

## 22.2 Error handling

```txt
Use domain exceptions or Result pattern with error_code.
API maps error_code to HTTP response.
```

## 22.3 Correlation ID

```txt
Generate/propagate correlation_id per request/job.
```

## 22.4 Celery correlation

```txt
Celery tasks receive correlation_id.
Events and AIUsageLog include same correlation_id.
```

---

# 23. Enums / JSON / relational modeling

## 23.1 TextChoices

```txt
Use Django TextChoices for statuses/types.
```

## 23.2 JSONField

```txt
Use JSONField for payload/metadata.
Use relational tables for query-critical relations.
```

Use JSONField for:
- event payload ;
- upload metadata ;
- AI structured output ;
- settings-like metadata.

Do not use JSONField for:
- detected_domains ;
- membership_domains ;
- query-critical relations ;
- assignee/roles.

---

# 24. Index strategy

## 24.1 MVP query paths

```txt
Index MVP query paths:
- establishment_id
- status
- role/domain joins
- last_activity_at
- due_at
- assigned_to
- created_by
- recipient/status
```

## 24.2 Signals

Recommended indexes:
- `(establishment_id, status)`
- `(establishment_id, pinned)`
- `(establishment_id, urgency)`
- `(establishment_id, last_activity_at)`
- signal detected domain join indexes.

## 24.3 Actions

Recommended indexes:
- `(establishment_id, status)`
- `(assigned_to_id, status)`
- `(created_by_id, status)`
- `(signal_id)`
- `(due_at)`

## 24.4 Notifications

Recommended indexes:
- `(recipient_id, status, created_at)`
- `(establishment_id, recipient_id)`

## 24.5 Events

Recommended indexes:
- `(event_type)`
- `(category)`
- `(establishment_id)`
- `(organization_id)`
- `(subject_type, subject_id)`
- `(correlation_id)`
- unique partial index on `idempotency_key` when not null.

---

# 25. Feed implementation

## 25.1 Query approach

```txt
Use ORM QuerySets with select_related/prefetch_related.
Add raw SQL only for complex union feed if needed.
```

## 25.2 Execution Feed union

```txt
MVP: query per item type, normalize, merge/sort in Python.
Optimize later if volume requires.
```

## 25.3 Serializers

```txt
Use explicit DRF serializers for read models/feed items.
Avoid exposing raw models.
```

## 25.4 ActivityUpdater

```txt
ActivityUpdater consumer updates last_activity_at.
```

---

# 26. Testing

## 26.1 Test framework

```txt
Use pytest + pytest-django.
Domain service tests first.
API tests for critical endpoints.
```

## 26.2 Factories

```txt
Use factory_boy for tests.
```

## 26.3 Test priority

1. Domain services.
2. Permissions.
3. Feed queries.
4. Auth/session/refresh.
5. AI contracts.
6. Event dispatch.
7. Notification matrix.
8. Realtime authorization.
9. Upload lifecycle.
10. API integration.

---

# 27. Typing / lint / package management

## 27.1 Type checking

```txt
Use type hints on services and Pydantic schemas.
Gradual type checking.
```

## 27.2 Ruff

```txt
Use Ruff for lint/format.
Optionally mypy/pyright for typing.
```

## 27.3 uv

```txt
Use uv with locked dependencies.
```

---

# 28. Docker Compose local

## 28.1 Services

```txt
Docker Compose:
- api
- postgres
- redis
- celery_worker
- celery_beat
- frontend
- object_storage local optional
```

## 28.2 MinIO

```txt
Use MinIO locally.
Use S3-compatible provider in prod.
```

---

# 29. Admin / Support

## 29.1 Django Admin

```txt
Use Django Admin for internal support/admin MVP.
Restrict access strongly.
```

## 29.2 Raw Observations

```txt
Raw Observations accessible only via controlled admin/database support.
Never in product UI.
```

## 29.3 Admin support model

```txt
Include minimal admin/support access model.
Detailed Admin Tooling post-ERD/P1.
```

---

# 30. Environment / deployment

## 30.1 Settings

```txt
Use environment-based settings.
Pydantic Settings acceptable.
```

## 30.2 Migrations

```txt
Use standard Django migrations per app.
```

## 30.3 Seeds / defaults

```txt
Use idempotent management commands for default modules/domains/templates.
```

## 30.4 Production shape

```txt
MVP deployable as Docker services:
api ASGI
celery_worker
celery_beat
redis
postgres
object storage external
Django serves server-rendered product screens
static assets served via CDN/object storage if needed
no separate React frontend hosting for MVP
```

---

# 31. ERD logical overview

```txt
Organization
└── Establishment
    ├── EstablishmentMembership
    │   ├── User
    │   └── MembershipDomain
    │       └── OperationalDomain
    ├── OperationalDomain
    ├── OperationalModule / EstablishmentOperationalModule
    ├── OperationalUnit
    ├── EstablishmentKnowledgeItem
    ├── Observation
    │   ├── ObservationProcessing
    │   ├── ObservationMedia
    │   └── ObservationSignalLink
    │       └── Signal
    ├── Signal
    │   ├── SignalDetectedDomain
    │   ├── Action
    │   └── Comment
    ├── ChecklistTemplate
    │   ├── ChecklistTaskTemplate
    │   └── ChecklistExecution
    │       └── ChecklistTaskExecution
    ├── Notification
    │   └── NotificationDelivery
    ├── TemporaryUpload
    ├── ApplicationEvent
    │   └── EventDelivery
    ├── AIUsageLog
    │   └── AIStructuredOutput
    └── Comments / Mentions
```

---

# 32. App ownership

## 32.1 accounts

Owns:
- User
- UserSession
- Invitation
- authentication services
- password reset
- token rotation

## 32.2 organizations

Owns:
- Organization
- future billing anchor if changed later

## 32.3 establishments

Owns:
- Establishment
- EstablishmentMembership
- OperationalDomain
- OperationalModule
- OperationalUnit
- EstablishmentKnowledgeItem
- membership domain assignments
- permissions

## 32.4 observations

Owns:
- Observation
- ObservationProcessing
- ObservationSignalLink
- observation submission flow

## 32.5 uploads

Owns:
- TemporaryUpload
- ObservationMedia
- signed URLs
- storage adapter
- cleanup jobs

## 32.6 signals

Owns:
- Signal
- SignalDetectedDomain
- signal lifecycle
- aggregation/linking outcomes
- last_activity_at update coordination

## 32.7 actions

Owns:
- Action
- action lifecycle
- validation/reopen/cancel

## 32.8 checklists

Owns:
- ChecklistTemplate
- ChecklistTaskTemplate
- ChecklistExecution
- ChecklistTaskExecution
- domains joins

## 32.9 comments

Owns:
- Comment
- CommentMention

## 32.10 notifications

Owns:
- Notification
- NotificationDelivery
- notification matrix
- deliveries

## 32.11 events

Owns:
- ApplicationEvent
- EventDelivery
- event publish/dispatch
- event consumers

## 32.12 realtime

Owns:
- Channels
- RealtimeBroadcaster
- channel authorization

## 32.13 ai

Owns:
- AIUsageLog
- AIStructuredOutput
- Pydantic contracts
- AI provider abstraction
- transcription/onboarding/pipeline services

---

# 33. Recommended service modules

```txt
accounts/services.py
accounts/tokens.py
accounts/invitations.py

establishments/permissions.py
establishments/services.py
establishments/selectors.py

observations/services.py
observations/processing.py
observations/selectors.py

signals/services.py
signals/aggregation.py
signals/selectors.py

actions/services.py
actions/selectors.py

checklists/services.py
checklists/selectors.py

notifications/matrix.py
notifications/services.py
notifications/deliveries.py

events/publish.py
events/dispatch.py
events/consumers.py

realtime/broadcaster.py
realtime/consumers.py
realtime/permissions.py

uploads/services.py
uploads/storage.py
uploads/cleanup.py

ai/providers.py
ai/transcription.py
ai/onboarding.py
ai/observation_pipeline.py
ai/schemas.py
```

---

# 34. Decisions index

| Décision | Statut |
|---|---:|
| Modular monolith Django | Validé |
| One deployable backend | Validé |
| Django apps as domain boundaries | Validé |
| apps structure with `ai` and `events` | Validé |
| User/UserSession/Invitation in accounts | Validé |
| EstablishmentMembership in establishments | Validé |
| UUID primary keys everywhere | Validé |
| created_at/updated_at everywhere | Validé |
| Soft delete limited | Validé |
| Authorization via current Membership DB/cache | Validé |
| Organization has_many Establishments | Validé |
| Billing future belongs to Establishment | Validé |
| User global + EstablishmentMembership | Validé |
| User model with email/username identities | Validé |
| Membership domains join table | Validé |
| SignalDetectedDomain table | Validé |
| OperationalDomain table scoped establishment | Validé |
| OperationalModule table | Validé |
| OperationalUnit table | Validé |
| EstablishmentKnowledgeItem typed table | Validé |
| Observation model | Validé |
| ObservationProcessing model | Validé |
| ObservationProcessing outcome enum | Validé |
| ObservationMedia model | Validé |
| TemporaryUpload model | Validé |
| Signal model | Validé |
| ObservationSignalLink many-to-many | Validé |
| No durable SignalCandidate table MVP, AI output retained 14d | Recommandé |
| Action model | Validé |
| Action.priority stored, derived from Signal urgency MVP | Validé |
| Checklist 4 models | Validé |
| Shared/Personal via type fields | Validé |
| TaskExecution snapshots | Validé |
| Checklist domains joins | Validé |
| Polymorphic Comment | Validé |
| CommentMention table | Validé |
| Notification + NotificationDelivery | Validé |
| ApplicationEvent + EventDelivery | Validé |
| AIUsageLog | Validé |
| AIStructuredOutput 14 days | Validé |
| Redis broker Celery | Validé |
| Task results disabled/minimal | Validé |
| Shared Redis acceptable with separate DB/prefixes | Validé |
| Pydantic for AI schemas, DRF serializers for API | Validé |
| drf-spectacular + generated TS client | Validé |
| REST-first + command endpoints | Validé |
| Domain services/use-cases | Validé |
| transaction.atomic + events after commit | Validé |
| Domain exceptions/Result error_code | Validé |
| Django TextChoices | Validé |
| JSONField for payload/metadata only | Validé |
| Index MVP query paths | Validé |
| establishment_id on runtime tables | Validé |
| organization_id denormalized in events/logs if useful | Validé |
| Actor fields where product needs them + events audit | Validé |
| ActivityUpdater consumer | Validé |
| ORM optimized first, raw SQL only if needed | Validé |
| Execution Feed merge/sort Python MVP | Validé |
| Explicit DRF serializers/read models | Validé |
| pytest + pytest-django | Validé |
| factory_boy | Validé |
| Type hints gradual typing | Validé |
| Ruff | Validé |
| uv | Validé |
| Docker Compose local | Validé |
| MinIO local | Validé |
| Django Admin internal support MVP | Validé |
| Raw Observations admin/database only | Validé |
| Minimal admin/support model in ERD | Validé |
| Centralized permission services | Validé |
| Query/selectors modules | Validé |
| Plural app names | Validé |
| Small core app | Validé |
| Avoid common/ | Validé |
| /api/v1 URL versioning | Validé |
| Standard error response | Validé |
| correlation_id middleware | Validé |
| Celery correlation propagation | Validé |
| Standard Django migrations per app | Validé |
| Idempotent management commands | Validé |
| Environment-based settings | Validé |
| Dockerized production shape | Validé |

---

# 35. Points à traiter dans l’API Contract

Le prochain document doit transformer cette architecture en endpoints.

À cadrer :
- auth endpoints ;
- invitation endpoints ;
- current context / establishment switch ;
- onboarding endpoints ;
- observation submit/upload endpoints ;
- signal feed/detail/actions ;
- action transitions ;
- checklist templates/executions/tasks ;
- comments/mentions ;
- notifications ;
- signed URLs ;
- websocket subscription contract ;
- error codes ;
- OpenAPI schemas.

---

# 36. Recommandation finale

Le Technical Architecture / ERD Final est suffisamment cadré pour passer au **API Contract MVP**.

Décision centrale :

```txt
Houston is a Django modular monolith.
The database is the source of business truth.
Events drive async consumers.
Feeds are authorized backend queries.
Realtime invalidates, API returns data.
```

Le build doit maintenant s’appuyer sur :
- Django apps par domaine ;
- UUID everywhere ;
- PostgreSQL relational modeling for query-critical relations ;
- Celery + Redis for async jobs ;
- Channels + Redis for realtime ;
- DRF + drf-spectacular for OpenAPI ;
- Pydantic for AI contracts ;
- services/use-cases for business writes ;
- selectors/query services for reads ;
- pytest/factory_boy for testability ;
- Docker Compose + MinIO local.
