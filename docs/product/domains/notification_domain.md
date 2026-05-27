# Notification Domain

Status: authoritative
Last reviewed: 2026-05-27
Implementation status: not_started

## 1. Purpose

This domain defines Houston's user-facing attention messages generated from backend events and product notification rules.

Notification owns:
- recipient resolution after backend visibility and RBAC re-check
- priority and channel selection
- persisted in-app notification state
- delivery tracking when channel delivery is implemented

Notification does not own:
- event persistence or event catalog definition
- realtime transport or invalidation
- feed projection or feed sorting
- authorization or access grants
- Signal, Action, Checklist, Comment, or Chat lifecycle

## 2. MVP Scope

- Notifications are attention messages, not business truth.
- One event may generate zero, one, or many notifications depending on notification rules.
- Persisted in-app notifications for authorized recipients are in MVP direction.
- A simple Notification Center for the authenticated recipient is in MVP direction.
- Backend-owned recipient resolution, priority selection, and channel selection from domain events.
- Minimal, non-sensitive notification payloads that point to an authenticated subject fetch.
- Per-recipient read and archive state.
- Candidate push delivery for selected high-attention cases when implemented.
- Targeted mention notifications without permission grants.

Current truth:
- `apps/api/houston/notifications/` is only a Django app stub today.
- `apps/api/schema.yml` confirms no notification endpoints today.

## 3. Out of Scope

- General-purpose email notifications in MVP.
- SMS, WhatsApp, or other external messaging channels.
- Quiet hours, digests, grouping, or presence-aware suppression.
- Rich media, attachments, or media binaries inside notifications.
- Notification-based access grants or notification-based business truth.
- Chat notifications are out of MVP until `chat_domain.md` validates them.
- Full provider setup or push runbook details.
- Full admin notification console or analytics dashboard.
- Cross-tenant notifications.
- Marketing notifications.

## 4. Core Invariants

- Notification is a user attention message, not an Event, not Realtime, and not Feed.
- Notification is generated from backend event handling and product rules, but it is not the event itself.
- Notifications never grant access.
- Backend must re-check recipient visibility and RBAC before creating a notification.
- Notification payloads must be minimal and non-sensitive.
- Notification payloads must not include raw Observation text, complete comment bodies, chat message bodies, media binaries, credentials, auth artifacts, or AI request content.
- Opening a notification must fetch the target resource through the normal authenticated and authorized API flow.
- Realtime and push delivery failures must not roll back the originating business action.
- Actor self-notification is excluded by default for normal user actions.
- Read and archive state is per recipient.
- Realtime invalidation does not replace persisted in-app notifications.
- Notification Center does not replace Feed.
- Target channel direction is `info` -> `in_app`, `action_required` -> `in_app` and candidate `push`, `urgent` -> `in_app` and candidate `push`, `system` -> `in_app` or selective email depending on type.

## 5. Main Objects

- `Notification`
  - Persisted attention item for one recipient.
  - Points to a subject resource and source event context without becoming business truth.

- `NotificationRecipient`
  - Authorized user selected after establishment scope and RBAC checks.
  - Notification visibility is limited to that recipient.

- `NotificationPriority`
  - Target values are `info`, `action_required`, `urgent`, and `system`.
  - Priority influences expected delivery channel choice.

- `NotificationChannel`
  - `in_app` is the validated MVP direction.
  - `push` is candidate until implemented.
  - `email` remains selective or post-MVP unless separately validated.

- `NotificationDelivery`
  - Per-channel delivery attempt or outcome when delivery tracking is implemented.
  - Exact provider metadata remains candidate.

- `NotificationPreference`
  - Minimal recipient/channel preference such as `push_enabled` or candidate `email_enabled`.
  - Preferences suppress delivery channels, not resource access.

- `NotificationRule`
  - Product rule that maps source event and context to recipients, priority, and channels.
  - Exact storage and service design are not validated in current code.

- `NotificationDeduplication`
  - Candidate anti-noise rule to avoid duplicate notifications for the same recipient, event, and subject window.
  - Exact dedup window remains candidate until implemented.

## 6. Lifecycle / Statuses

Notification lifecycle target behavior:
- `unread`
- `read`
- `archived`

Delivery lifecycle target behavior:
- `queued`
- `sent`
- `delivered`
- `failed`
- `skipped`

Target transition direction:
- event processed by notification rules -> zero, one, or many notifications
- notification created -> `unread`
- recipient marks read -> `read`
- recipient archives -> `archived`
- delivery attempt created -> `queued` then `sent`, `delivered`, `failed`, or `skipped`

Current code does not validate notification models, services, or delivery pipelines yet.

## 7. Permissions

- A user may only list or update their own notifications.
- Notification creation requires recipient eligibility after backend establishment scope and RBAC checks.
- Notification visibility does not grant subject visibility.
- Opening a notification must pass the normal authorized fetch for the target resource.
- Push delivery does not bypass authentication or authorization.
- Role-specific recipient rules depend on adjacent domain rules and notification rules, not on frontend logic.
- Support or admin access to product notifications is not validated as default MVP behavior.

## 8. Events

No implemented notification event contract is validated in current code or in `apps/api/schema.yml`.

Candidate notification-domain events only:
- `NotificationCreated`
- `NotificationRead`
- `NotificationArchived`
- `NotificationDeliveryQueued`
- `NotificationDeliverySucceeded`
- `NotificationDeliveryFailed`
- `NotificationDeliverySkipped`

Candidate source-trigger families only:
- Signal events such as `SignalCreated`, `SignalUrgencyChanged`, `SignalResolved`, and `SignalCanceled`
- Action events such as `ActionAssigned`, `ActionPendingValidation`, `ActionValidated`, `ActionReopened`, and `ActionCanceled`
- Checklist events such as `ChecklistExecutionAssigned`, `ChecklistExecutionDone`, and `ChecklistExecutionCanceled`
- mention or comment-related events on authorized Signal or Action context
- selected technical or onboarding failures with simplified, non-sensitive messaging

Validated boundary notes:
- Notification may consume events from Signal, Action, Checklist, Comments, Identity, or onboarding-related domains.
- Notification does not define the event catalog.
- `ChecklistExecutionAssigned` notifies the assignee.
- `ChecklistExecutionDone` notifies the user who assigned the checklist.
- Current MVP build direction keeps Chat isolated from Notifications; chat notification behavior is not validated.

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented notification endpoints confirmed in `apps/api/schema.yml`:
- none

Candidate endpoints only:
- list current user's notifications
- mark a notification as read
- archive a notification
- mark all notifications as read
- update minimal notification preferences such as `push_enabled` or `email_enabled`
- register or update a browser push subscription

Do not treat any notification endpoint as implemented until it exists in `apps/api/schema.yml`.

## 10. Frontend Expectations

- Notification Center lists the authenticated user's notifications only.
- Frontend must not treat notifications as source of business truth.
- Opening a notification should navigate to a safe route and then refetch the authorized subject through the backend API.
- Frontend must not display sensitive raw content from notification, push, or realtime payloads.
- Frontend must handle `unread`, `read`, and `archived` states when APIs exist.
- Frontend may optimistically update read state only if backend confirmation or reconciliation remains the authority.
- TanStack Query owns notification server state when notification APIs exist.
- Frontend must use generated OpenAPI clients only for routes present in `apps/api/schema.yml`.
- Realtime remains invalidation and refetch only; it does not replace persisted notifications.

## 11. AI Agent Notes

- Inspect current notification code before claiming models, services, delivery tracking, providers, or notification rules exist.
- Inspect `apps/api/schema.yml` before listing any notification API as implemented.
- Inspect `rbac_permissions_domain.md` before changing recipient resolution or visibility assumptions.
- Inspect `security_rgpd_domain.md` before changing payload contents, retention assumptions, or logging boundaries.
- Inspect Signal, Action, Checklist, Feed, and adjacent product docs before changing notification trigger assumptions.
- Do not make Notification a source of truth.
- Do not grant access through notifications.
- Do not include raw Observation text, complete comment bodies, chat message bodies, media binaries, credentials, auth artifacts, or AI request content in notifications.
- Do not add general-purpose email workflows in MVP unless separately validated.
- Do not notify the actor for their own normal action by default.
- Do not add grouping, digests, quiet hours, or provider-specific push setup to this domain doc unless separately validated.
- When notification APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
