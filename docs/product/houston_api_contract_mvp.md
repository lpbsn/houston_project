# Houston — API Contract MVP

**Version:** v0.1  
**Date:** 2026-05-26  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — HTTP API, endpoints, schemas, errors, permissions, pagination, realtime contract, OpenAPI

**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(20).txt`

**Documents liés :**
- `Houston_technical_architecture_erd_final.md`
- `Houston_authentication_identity_domain.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_onboarding_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`
- `Houston_notification_matrix.md`
- `Houston_upload_media_lifecycle.md`
- `Houston_realtime_architecture.md`
- `Houston_feed_query_sorting_contract.md`

---

# 1. Objectif du document

Ce document formalise le **API Contract MVP** de Houston.

Il définit :
- les endpoints ;
- les méthodes HTTP ;
- les request schemas ;
- les response schemas ;
- les error codes ;
- les permissions ;
- la pagination ;
- le realtime/refetch behavior ;
- les conventions OpenAPI ;
- les conventions de dates, IDs, erreurs et headers.

Ce document sert de base pour :
- Django REST Framework ;
- drf-spectacular ;
- endpoints JSON ;
- tests API ;
- futurs consommateurs API/mobile ;
- modules TypeScript ciblés si nécessaire.

---

# 2. Principe central

```txt
API exposes authorized product workflows.
Not raw database CRUD.
Backend owns business rules.
OpenAPI documents the contract.
```

En français :

```txt
L’API expose des workflows produit autorisés.
Elle n’expose pas un CRUD brut de base de données.
Le backend possède les règles métier.
OpenAPI documente le contrat.
```

## 2.1 Web app rendering strategy

The MVP web app uses a thin React frontend backed by backend-owned APIs.

```txt
React renders product screens.
TanStack Query consumes backend APIs.
DRF exposes JSON APIs.
OpenAPI documents the frontend/backend contract.
```

---

# 3. Style API

## 3.1 REST-first

```txt
REST-first API.
Command endpoints for domain transitions.
```

Exemples :

```txt
POST /actions/:id/accept
POST /actions/:id/mark_done
POST /signals/:id/resolve
```

## 3.2 Versioning

```txt
All endpoints under /api/v1/
```

## 3.3 IDs

```txt
All public API IDs are UUID strings.
```

## 3.4 Date format

```txt
All datetimes in ISO 8601 UTC.
Frontend handles display timezone.
```

## 3.5 Nullable fields

```txt
Use explicit null for nullable fields.
Do not omit documented fields.
```

---

# 4. Response conventions

## 4.1 Single resource

```txt
Single resource response = object direct
```

## 4.2 Collection / feed

```txt
Collection/feed response = envelope with items/pagination
```

Format :

```json
{
  "items": [],
  "next_cursor": "string|null",
  "has_more": true,
  "applied_filters": {},
  "counts": {}
}
```

## 4.3 Errors

```txt
Errors = standard error envelope
```

Format :

```json
{
  "error": {
    "code": "ACTION_NOT_ALLOWED",
    "message": "Human readable message",
    "details": {}
  }
}
```

## 4.4 Error language

```txt
error.code = stable English code
error.message = human-readable fallback
frontend can map codes to French UX copy
```

---

# 5. Error status conventions

## 5.1 Auth errors

```txt
401 UNAUTHENTICATED
401 TOKEN_EXPIRED
401 REFRESH_TOKEN_INVALID
```

## 5.2 Validation / permission / conflict

```txt
400 VALIDATION_ERROR for request validation.
409 BUSINESS_CONFLICT for state conflicts.
403 ACTION_NOT_ALLOWED for permission.
```

## 5.3 Invalid filters

```txt
Invalid filter → 400 INVALID_FILTER
```

## 5.4 Visibility vs permission

```txt
403 for action not allowed on visible resource.
404 for resource not visible / outside tenant.
```

## 5.5 Rate limit

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests",
    "details": {
      "retry_after_seconds": 60
    }
  }
}
```

---

# 6. Headers

## 6.1 Idempotency

```txt
Support Idempotency-Key header for:
- Observation submit
- Action create
- Checklist execution create
- Invitation create
```

## 6.2 Correlation ID

```txt
Request header: X-Correlation-ID optional
Response header: X-Correlation-ID always
```

---

# 7. Authentication API

## 7.1 Endpoints

```txt
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/logout_all
GET  /api/v1/auth/me
POST /api/v1/auth/switch_establishment
```

## 7.2 Login request

Supports both email identity and username identity.

```json
{
  "identifier": "mama_nice_hk_024",
  "password": "string"
}
```

## 7.3 Login response

```json
{
  "access_token": "jwt",
  "expires_in": 900,
  "user": {},
  "active_memberships": [],
  "selected_establishment_id": "uuid|null"
}
```

## 7.4 Refresh

```txt
POST /auth/refresh
→ rotates refresh token
→ returns new access token
```

## 7.5 Me endpoint

```txt
GET /auth/me returns:
- current user
- active memberships
- current establishment context
- role/domains for selected membership
```

## 7.6 Switch establishment

```txt
POST /auth/switch_establishment
```

Payload :

```json
{
  "establishment_id": "uuid"
}
```

---

# 8. Invitations API

## 8.1 Endpoints

```txt
POST /api/v1/establishments/:id/invitations
GET  /api/v1/establishments/:id/invitations
POST /api/v1/invitations/:token/accept
POST /api/v1/invitations/:id/resend
POST /api/v1/invitations/:id/revoke
```

## 8.2 Staff username invitation request

```json
{
  "identity_type": "username",
  "first_name": "string",
  "last_name": "string",
  "role": "staff",
  "operational_domain_ids": ["uuid"]
}
```

## 8.3 Staff username invitation response

```json
{
  "login_identifier": "mama_nice_hk_024",
  "temporary_password": "shown_once"
}
```

Security rule:

```txt
temporary_password is shown once.
```

---

# 9. Password reset API

## 9.1 Endpoints

```txt
POST /api/v1/auth/password_reset/request
POST /api/v1/auth/password_reset/confirm
POST /api/v1/establishments/:id/users/:user_id/reset_password
```

## 9.2 Staff username identity

```txt
POST /establishments/:id/users/:user_id/reset_password
```

This endpoint is for Staff username identity and is restricted to authorized Manager/Director/Owner.

---

# 10. Memberships API

## 10.1 Endpoints

```txt
GET  /api/v1/establishments/:id/memberships
GET  /api/v1/establishments/:id/memberships/:membership_id
PATCH /api/v1/establishments/:id/memberships/:membership_id
POST /api/v1/establishments/:id/memberships/:membership_id/deactivate
```

## 10.2 Patch membership request

```json
{
  "role": "manager",
  "operational_domain_ids": ["uuid"]
}
```

---

# 11. User search API

## 11.1 Endpoint

```txt
GET /api/v1/establishments/:id/users/search?q=
```

## 11.2 Purpose

Used for:
- assignment ;
- mentions ;
- Staff / Manager search ;
- domain-filtered selection.

## 11.3 Assignee recommendation

```txt
MVP: user search + domain filter.
Post-MVP: recommended assignees.
```

---

# 12. Onboarding API

## 12.1 Endpoints

```txt
POST /api/v1/onboarding/sessions
GET  /api/v1/onboarding/sessions/:id
POST /api/v1/onboarding/sessions/:id/submit_description
POST /api/v1/onboarding/sessions/:id/run_ai
PATCH /api/v1/onboarding/sessions/:id/proposal
POST /api/v1/onboarding/sessions/:id/validate_section
POST /api/v1/onboarding/sessions/:id/activate
```

## 12.2 Proposal sections

```txt
proposal sections:
- operational_modules
- operational_domains
- operational_units
- runtime_vocabulary
- runtime_tags
- routing_hints
```

---

# 13. Establishment runtime configuration API

## 13.1 Establishment

```txt
GET   /api/v1/establishments/:id
PATCH /api/v1/establishments/:id
```

## 13.2 Operational domains

```txt
GET   /api/v1/establishments/:id/operational_domains
POST  /api/v1/establishments/:id/operational_domains
PATCH /api/v1/establishments/:id/operational_domains/:domain_id
```

## 13.3 Operational units

```txt
GET   /api/v1/establishments/:id/operational_units
POST  /api/v1/establishments/:id/operational_units
PATCH /api/v1/establishments/:id/operational_units/:unit_id
```

## 13.4 Knowledge items

```txt
GET   /api/v1/establishments/:id/knowledge_items
POST  /api/v1/establishments/:id/knowledge_items
PATCH /api/v1/establishments/:id/knowledge_items/:knowledge_item_id
```

---

# 14. Observation API

## 14.1 Submit observation

```txt
POST /api/v1/establishments/:id/observations
```

Request :

```json
{
  "raw_text": "string",
  "source": "direct",
  "checklist_execution_id": "uuid|null",
  "checklist_task_execution_id": "uuid|null",
  "operational_unit_id": "uuid|null",
  "temporary_upload_ids": ["uuid"]
}
```

Response :

```json
{
  "observation_id": "uuid",
  "status": "submitted",
  "processing_status": "queued",
  "message": "Observation reçue"
}
```

## 14.2 No raw Observation product endpoint

```txt
No product API endpoint returning raw Observation detail.
Admin/support only if needed.
```

---

# 15. Upload API

## 15.1 Temporary uploads

```txt
POST   /api/v1/establishments/:id/temporary_uploads
DELETE /api/v1/establishments/:id/temporary_uploads/:upload_id
```

## 15.2 Upload format

```txt
Temporary upload endpoint uses multipart/form-data.
```

---

# 16. Transcription API

## 16.1 Endpoint

```txt
POST /api/v1/establishments/:id/transcriptions
```

Payload :
- temporary audio upload id.

Response :

```json
{
  "transcription": "string",
  "language": "fr-FR",
  "duration_ms": 4200,
  "correlation_id": "uuid"
}
```

---

# 17. Signal Feed API

## 17.1 Endpoint

```txt
GET /api/v1/establishments/:id/signal_feed
```

## 17.2 Query params

```txt
view_mode
domains[]
statuses[]
urgency
search
cursor
page_size
```

---

# 18. Signal Detail API

## 18.1 Endpoint

```txt
GET /api/v1/establishments/:id/signals/:signal_id
```

## 18.2 Response constraints

Signal detail includes:
- title ;
- structured_summary ;
- status ;
- urgency ;
- domains ;
- actions summary ;
- comments summary ;
- events summary ;
- media references ;
- permissions.

It must not include:
- raw Observation text.

---

# 19. Signal Command API

## 19.1 Endpoints

```txt
POST /api/v1/signals/:id/resolve
POST /api/v1/signals/:id/cancel
POST /api/v1/signals/:id/pin
POST /api/v1/signals/:id/unpin
POST /api/v1/signals/:id/set_urgency
POST /api/v1/signals/:id/add_domain
POST /api/v1/signals/:id/remove_domain
```

## 19.2 Resolve request

```json
{
  "reason": "string"
}
```

## 19.3 Cancel request

```json
{
  "category": "false_alert|duplicate|invalid|other",
  "reason": "string"
}
```

## 19.4 Add/remove domain request

```json
{
  "operational_domain_id": "uuid",
  "reason": "string|null"
}
```

---

# 20. Action API

## 20.1 Create Action from Signal

```txt
POST /api/v1/establishments/:id/signals/:signal_id/actions
```

Request :

```json
{
  "title": "string",
  "description": "string|null",
  "assigned_to_id": "uuid",
  "due_at": "datetime|null"
}
```

## 20.2 Action detail

```txt
GET /api/v1/establishments/:id/actions/:action_id
```

## 20.3 Action commands

```txt
POST /api/v1/actions/:id/accept
POST /api/v1/actions/:id/mark_done
POST /api/v1/actions/:id/validate
POST /api/v1/actions/:id/reopen
POST /api/v1/actions/:id/cancel
POST /api/v1/actions/:id/reassign
PATCH /api/v1/actions/:id
```

## 20.4 Action cancel request

```json
{
  "category": "not_needed|duplicate|invalid|other",
  "comment": "string|null"
}
```

## 20.5 Action reopen request

```json
{
  "reason": "string"
}
```

---

# 21. Execution Feed API

## 21.1 Endpoint

```txt
GET /api/v1/establishments/:id/execution_feed
```

## 21.2 Query params

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

---

# 22. Checklist Template API

## 22.1 Template endpoints

```txt
GET  /api/v1/establishments/:id/checklist_templates
POST /api/v1/establishments/:id/checklist_templates
GET  /api/v1/establishments/:id/checklist_templates/:template_id
PATCH /api/v1/establishments/:id/checklist_templates/:template_id
POST /api/v1/checklist_templates/:id/activate
POST /api/v1/checklist_templates/:id/archive
```

## 22.2 Task Template endpoints

```txt
POST   /api/v1/checklist_templates/:id/tasks
PATCH  /api/v1/checklist_template_tasks/:task_id
DELETE /api/v1/checklist_template_tasks/:task_id
POST   /api/v1/checklist_templates/:id/tasks/reorder
```

---

# 23. Checklist Execution API

## 23.1 Create execution from template

```txt
POST /api/v1/checklist_templates/:id/executions
```

Request :

```json
{
  "assigned_to_id": "uuid",
  "due_at": "datetime|null"
}
```

## 23.2 Execution commands

```txt
POST /api/v1/checklist_executions/:id/start
POST /api/v1/checklist_executions/:id/cancel
GET  /api/v1/checklist_executions/:id
```

---

# 24. Personal Checklist API

## 24.1 Facade endpoints

```txt
GET  /api/v1/establishments/:id/personal_checklists
POST /api/v1/establishments/:id/personal_checklists
POST /api/v1/personal_checklists/:id/start
```

Backend can map these to ChecklistTemplate/ChecklistExecution with `template_type=personal`.

---

# 25. Checklist Task Execution API

## 25.1 Endpoints

```txt
POST /api/v1/checklist_task_executions/:id/complete
POST /api/v1/checklist_task_executions/:id/skip
POST /api/v1/checklist_task_executions/:id/create_observation
```

## 25.2 Create Observation from task

Request :

```json
{
  "raw_text": "string",
  "temporary_upload_ids": ["uuid"]
}
```

Backend adds:
- checklist_execution_id ;
- checklist_task_execution_id ;
- source=checklist.

---

# 26. Comments API

## 26.1 Signal comments

```txt
GET  /api/v1/signals/:id/comments
POST /api/v1/signals/:id/comments
```

## 26.2 Action comments

```txt
GET  /api/v1/actions/:id/comments
POST /api/v1/actions/:id/comments
```

## 26.3 Request

```json
{
  "body": "string",
  "mentioned_user_ids": ["uuid"]
}
```

---

# 27. Notifications API

## 27.1 Endpoints

```txt
GET  /api/v1/establishments/:id/notifications
POST /api/v1/notifications/:id/mark_read
POST /api/v1/notifications/:id/archive
POST /api/v1/notifications/mark_all_read
```

## 27.2 Bulk MVP

```txt
MVP bulk:
POST /notifications/mark_all_read
No bulk action lifecycle MVP.
```

---

# 28. Media API

## 28.1 Signed URL

```txt
POST /api/v1/establishments/:id/media/:media_id/signed_url
```

Response :

```json
{
  "url": "string",
  "expires_in": 600
}
```

## 28.2 Feed media fields

```json
{
  "media_count": 2,
  "thumbnail_media_id": "uuid|null"
}
```

Feeds return media references/counts, not signed URLs.

---

# 29. Event Timeline API

## 29.1 Endpoints

```txt
GET /api/v1/signals/:id/events
GET /api/v1/actions/:id/events
```

## 29.2 Constraint

```txt
Return safe projected timeline, not raw ApplicationEvent payload.
```

---

# 30. Detail response permissions

## 30.1 Detail permissions object

```json
{
  "permissions": {
    "can_create_action": true,
    "can_resolve": false,
    "can_comment": true
  }
}
```

## 30.2 Feed item actionability

For SignalFeedItem :

```json
{
  "can_act": true,
  "can_comment": true
}
```

---

# 31. Signal and Action detail composition

## 31.1 Signal detail

```txt
Signal detail includes summaries.
Comments/events/media can have dedicated endpoints if needed.
Include recent comments/events.
Paginate if volume grows.
```

## 31.2 Action detail

```txt
Action detail returns:
- action comments
- parent signal comments as contextual read-only section
```

---

# 32. WebSocket contract

## 32.1 Channels

```txt
WebSocket channels:
- EstablishmentFeedChannel
- UserExecutionChannel
- UserNotificationChannel
- SignalDetailChannel
- ActionDetailChannel
```

## 32.2 Behavior

Realtime payloads invalidate/refetch API queries.

No raw Observation text.  
No full comments.  
No media payloads.  
No object snapshot MVP.

---

# 33. Pagination

## 33.1 Feeds

```txt
Feeds = cursor pagination.
```

## 33.2 Admin/config small lists

```txt
Admin/config small lists = page/page_size or simple list.
```

---

# 34. AI API exposure

## 34.1 No generic public AI endpoint

```txt
No generic public AI endpoint.
```

Expose only:
- transcription ;
- onboarding AI trigger ;
- observation submit triggers pipeline async.

---

# 35. Admin/support API

## 35.1 MVP

```txt
MVP support mostly Django Admin.
Product API excludes admin raw Observation endpoints.
```

---

# 36. OpenAPI

## 36.1 Requirement

```txt
All product API endpoints must be OpenAPI documented.
```

## 36.2 Schema naming

```txt
Use explicit schemas:
SignalFeedItem
SignalDetail
CreateActionRequest
ActionDetail
ValidationErrorResponse
```

---

# 37. Command endpoint responses

## 37.1 Return updated resource summary

```txt
Command endpoints return updated resource summary + emitted status.
```

Example :

```json
{
  "action": {},
  "event": {
    "type": "ActionAccepted"
  }
}
```

## 37.2 Event metadata

```txt
Return optional event_type/correlation_id, not raw event payload.
```

---

# 38. Tests API MVP

## 38.1 Auth login email/username

```txt
Given email identity or username identity
When valid identifier/password submitted
Then login returns access_token and active memberships
```

## 38.2 Staff username invite

```txt
Given Manager invites Staff without email
When identity_type=username is submitted
Then response returns login_identifier and temporary_password shown once
```

## 38.3 No raw Observation endpoint

```txt
Given Observation exists
When product API is called
Then no endpoint exposes raw Observation detail
```

## 38.4 Observation submit idempotency

```txt
Given Idempotency-Key header
When Observation submit is retried
Then duplicate Observation is not created
```

## 38.5 Signal detail permissions

```txt
Given Manager sees Signal in general view without matching domain
When Signal detail is fetched
Then permissions.can_create_action is false
```

## 38.6 Action command lifecycle

```txt
Given Action open assigned to user
When POST /actions/:id/accept
Then status becomes in_progress
And response includes ActionAccepted event metadata
```

## 38.7 Checklist task observation

```txt
Given checklist task execution
When create_observation is called
Then Observation is created with source=checklist
And checklist context is attached
```

## 38.8 Signed URL RBAC

```txt
Given user cannot see media subject
When signed_url endpoint is called
Then 404 or 403 is returned according to visibility
```

## 38.9 Invalid filter

```txt
Given invalid status filter
When feed endpoint is called
Then 400 INVALID_FILTER is returned
```

## 38.10 OpenAPI coverage

```txt
Given product API endpoint exists
When OpenAPI schema is generated
Then endpoint appears with explicit request/response schema
```

---

# 39. Decisions index

| Décision | Statut |
|---|---:|
| API Contract covers endpoints/schemas/errors/permissions/pagination/realtime/OpenAPI | Validé |
| REST-first + command endpoints | Validé |
| All endpoints under /api/v1/ | Validé |
| Single resource direct, collections envelope, errors envelope | Validé |
| Standard error envelope | Validé |
| Stable English error codes | Validé |
| UUID strings everywhere | Validé |
| Auth endpoints validated | Validé |
| Login via identifier | Validé |
| Login response with access_token/user/memberships | Validé |
| Refresh rotates token | Validé |
| GET /auth/me context | Validé |
| switch_establishment endpoint | Validé |
| Invitation endpoints | Validé |
| Staff username invitation identity_type=username | Validé |
| Password reset + manager-assisted Staff reset | Validé |
| Membership endpoints scoped to establishment | Validé |
| PATCH membership role/domains | Validé |
| Onboarding session endpoints | Validé |
| Onboarding proposal sections | Validé |
| Runtime config endpoints | Validé |
| Observation submit endpoint | Validé |
| No product raw Observation detail endpoint | Validé |
| Observation ack + queued response | Validé |
| Temporary upload endpoints | Validé |
| Transcription endpoint | Validé |
| Signal Feed endpoint | Validé |
| Signal detail no raw Observation | Validé |
| Signal command endpoints | Validé |
| Signal resolve reason | Validé |
| Signal cancel category + reason | Validé |
| Add/remove domain payload | Validé |
| Create Action from Signal | Validé |
| Action detail endpoint | Validé |
| Action command endpoints | Validé |
| Action cancel payload | Validé |
| Action reopen reason | Validé |
| Execution Feed endpoint | Validé |
| Checklist Template API | Validé |
| Checklist Task Template API | Validé |
| Checklist Execution from template | Validé |
| Personal Checklist facade | Validé |
| Checklist Execution commands | Validé |
| Checklist Task Execution commands | Validé |
| Checklist task create_observation | Validé |
| Comments nested by Signal/Action | Validé |
| Mentions via mentioned_user_ids | Validé |
| Notifications API | Validé |
| Signed media URL endpoint | Validé |
| Feed media_count + thumbnail_media_id, not signed URLs | Validé |
| WebSocket channels included | Validé |
| Feed response envelope | Validé |
| Cursor for feeds, simple pagination for config lists | Validé |
| Invalid filters 400 INVALID_FILTER | Validé |
| 403 visible/not allowed, 404 not visible/outside tenant | Validé |
| Auth error codes | Validé |
| 400 validation / 409 conflict / 403 permission | Validé |
| Idempotency-Key for critical creates | Validé |
| X-Correlation-ID request/response | Validé |
| Safe event timeline endpoints | Validé |
| Signal detail summaries + separable sections | Validé |
| Action detail includes parent Signal comments read-only | Validé |
| Detail permissions object | Validé |
| Feed item actionability flags | Validé |
| /auth/me user profile + membership context | Validé |
| User search endpoint | Validé |
| User search MVP, recommendations post-MVP | Validé |
| No generic public AI endpoint | Validé |
| Admin/support mostly Django Admin | Validé |
| All product endpoints OpenAPI documented | Validé |
| Explicit OpenAPI schema names | Validé |
| ISO 8601 UTC datetimes | Validé |
| Explicit null nullable fields | Validé |
| multipart/form-data uploads | Validé |
| 429 RATE_LIMITED retry_after | Validé |
| Command endpoints return updated resource summary | Validé |
| Optional event_type/correlation_id in command response | Validé |
| Bulk limited to mark_all_read | Validé |
| Final principle validé | Validé |

---

# 40. Recommandation finale

Le **API Contract MVP** est suffisamment cadré pour produire ensuite :
- le fichier OpenAPI initial ;
- les serializers DRF ;
- les viewsets/views ;
- les tests API ;
- un client TypeScript généré si un consommateur JSON en a besoin.

Décision centrale :

```txt
API exposes authorized product workflows.
Not raw database CRUD.
Backend owns business rules.
OpenAPI documents the contract.
```
