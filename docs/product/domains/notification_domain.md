# Notification Domain

Status: authoritative
Last reviewed: 2026-06-25
Implementation status: lot1_in_app

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
- Targeted mention notifications without operational permission grants. Mention on an execution comment grants read/thread access in the comments and action-plan domains; the notification itself does not grant access.

Current truth (Lot 1 in-app):
- `apps/api/houston/notifications/` implements persisted in-app notifications, recipient resolution, dedupe, and scheduling producers (`scheduling.py`).
- `apps/api/schema.yml` lists notification endpoints: list, mark-read, archive, mark-all-read, preferences.
- Frontend Notification Center uses TanStack Query (`features/notifications/`).
- Membership-scoped realtime invalidation (`notification.created` / `notification.updated` / `notification.bulk_updated`) refreshes the notification list and unread badge; transport is owned by `houston/realtime/` (see [`realtime_domain.md`](realtime_domain.md)).
- Lot 1 event keys are defined in `houston/notifications/constants.py` (`LOT1_EVENT_KEYS`); see [`notification_matrix_v0.2.md`](../notification_matrix_v0.2.md) §1.1.
- `notifications_enabled` on `EstablishmentMembership` suppresses in-app notification creation for that recipient.
- Web Push (VAPID + `WebPushSubscription`) is implemented for allowlisted Lot 1 event keys in `PUSH_V1_EVENT_KEYS` (`houston/notifications/push/constants.py`), gated by `HOUSTON_PUSH_ENABLED` and membership `push_enabled`.
- Chat push (`chat.message.received`) is allowlisted only with anti-spam guards: Redis conversation presence (`chat:presence:{membership_id}:{conversation_id}`, TTL 45s, heartbeat via `POST .../chat/conversations/{id}/presence/`) and push throttle (`push:chat:{conversation_id}:{recipient_membership_id}`, TTL 120s). In-app chat notification rules (dedupe 5 min) are unchanged.

## 3. Out of Scope

- General-purpose email notifications in MVP.
- SMS, WhatsApp, or other external messaging channels.
- Quiet hours, digests, grouping, or presence-aware suppression for non-chat notifications.
- Rich media, attachments, or media binaries inside notifications.
- Notification-based access grants or notification-based business truth.
- Chat sounds and message-body previews in notifications (in-app `chat.message.received` is in Lot 1; push chat is Lot D — see §8).
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
  - Implemented: same recipient + `dedupe_key` within 5 minutes skips duplicate creation (`DEDUPE_WINDOW` in `constants.py`).

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

Current code (Lot 1):
- `Notification` model with statuses `unread`, `read`, `archived`.
- In-app delivery only; push/email delivery tracking not implemented.

## 7. Permissions

- A user may only list or update their own notifications.
- Notification creation requires recipient eligibility after backend establishment scope and RBAC checks.
- Notification visibility does not grant subject visibility.
- Opening a notification must pass the normal authorized fetch for the target resource.
- Push delivery does not bypass authentication or authorization.
- Role-specific recipient rules depend on adjacent domain rules and notification rules, not on frontend logic.
- Support or admin access to product notifications is not validated as default MVP behavior.

## 8. Events

Lot 1 source triggers (implemented in `scheduling.py`; keys in `LOT1_EVENT_KEYS`):

- Action Plan execution: `action_plan.execution.created`, `action_plan.execution.pending_validation`, `action_plan.execution.canceled`, `action_plan.execution.reopened`
- Chat: `chat.message.received` (in-app + push when allowlisted and guards pass; generic copy with actor display name; `subject_type=chat_conversation`, `subject_id=conversation_id`; in-app dedupe per conversation + recipient + actor within 5 minutes; push suppressed when recipient presence is active in conversation or within 2-minute push throttle window)
- Comment: `comment.mention.created`
- Signal: `signal.created`, `signal.urgency_changed`, `signal.pinned`, `signal.resolved`, `signal.canceled`

Legacy `action.*` and `checklist.execution.*` keys removed in Lot 10A (migration `0004_remove_legacy_notification_enums`).

Intentionally no Lot 1 notification for: `accept_action`, `validate_action`, direct-done without validation, signal aggregation.

Candidate notification-domain transport events (membership-scoped WS invalidation via `notifications/services.py`):

- `notification.created`, `notification.updated`, `notification.bulk_updated`

Candidate Lot 2+ source triggers (not implemented): see [`notification_matrix_v0.2.md`](../notification_matrix_v0.2.md) §Lot2 backlog.

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented notification endpoints in `apps/api/schema.yml`:

- `GET /api/v1/establishments/{establishment_id}/notifications/` — list for authenticated recipient (cursor pagination); `NotificationItem` may include nullable `navigation` (`parent_subject_type`, `parent_subject_id`) for `subject_type=comment` when the comment row still exists
- `POST .../notifications/{notification_id}/mark-read/`
- `POST .../notifications/{notification_id}/archive/`
- `POST .../notifications/mark-all-read/`
- `GET` / `PATCH .../notifications/preferences/` — `notifications_enabled`, `push_enabled`
- `GET /api/v1/push/vapid-public-key/`
- `POST /api/v1/me/web-push-subscriptions/` (upsert), `POST .../{id}/touch/`, `DELETE .../{id}/` (revoke)
- `POST .../chat/conversations/{conversation_id}/presence/` — chat push presence heartbeat (204)

Not implemented:

- general-purpose email notification workflows

## 10. Frontend Expectations

- Notification Center lists the authenticated user's notifications only.
- Frontend must not treat notifications as source of business truth.
- Opening a notification should navigate to a safe route and then refetch the authorized subject through the backend API.
- Chat message notifications (`chat.message.received`): navigate to `/chat/{conversation_id}` (`subject_type=chat_conversation`). Notification copy must not include message body. While viewing a conversation, the client sends presence heartbeats (`POST .../presence/`, ~30s when visible) so push is suppressed server-side.
- Comment mention notifications (`comment.mention.created`): when `navigation` is present, open the parent detail (`signal` or `action_plan_execution`) with the Commentaires tab and scroll/highlight the mentioned comment (`?tab=comments&commentId={subject_id}`). When `navigation` is `null` (comment hard-deleted; V1 without denormalized parent on `Notification`), mark read only — no navigation. When the parent loads but the comment is absent from the authorized list, show an inline unavailable message in the Commentaires tab.
- `navigation` is a non-sensitive routing hint (parent type + UUID only); authorization remains on the parent and comment list fetches.
- Frontend must not display sensitive raw content from notification, push, or realtime payloads.
- Frontend must handle `unread`, `read`, and `archived` states when APIs exist.
- Frontend may optimistically update read state only if backend confirmation or reconciliation remains the authority.
- TanStack Query owns notification server state when notification APIs exist.
- Frontend must use generated OpenAPI clients only for routes present in `apps/api/schema.yml`.
- Realtime invalidates notification list queries on membership-scoped `notification.*` events; it does not replace persisted notifications.

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
