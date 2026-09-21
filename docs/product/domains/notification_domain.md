# Notification Domain

Status: authoritative
Implementation status: in-app notifications + native FCM push

## 1. Purpose

This domain defines Houston's user-facing attention messages generated from backend events and product notification rules.

Notification owns:
- recipient resolution after backend visibility and RBAC re-check
- priority and channel selection
- persisted in-app notification state
- native FCM delivery tracking (`PushDelivery`); other channels when implemented

Notification does not own:
- event persistence or event catalog definition
- realtime transport or invalidation
- feed projection or feed sorting
- authorization or access grants
- Signal, Action Plan, Comment, or Chat lifecycle

## 2. MVP Scope

- Notifications are attention messages, not business truth.
- One event may generate zero, one, or many notifications depending on notification rules.
- Persisted in-app notifications for authorized recipients are in MVP direction.
- A simple Notification Center for the authenticated recipient is in MVP direction.
- Backend-owned recipient resolution, priority selection, and channel selection from domain events.
- Minimal, non-sensitive notification payloads that point to an authenticated subject fetch.
- Per-recipient read and archive state.
- Native FCM push delivery for selected high-attention cases.
- Targeted mention notifications without operational permission grants. Mention on an execution comment grants read/thread access in the comments and action-plan domains; the notification itself does not grant access.

Current truth:
- `apps/api/houston/notifications/` implements persisted in-app notifications, recipient resolution, dedupe, and scheduling producers (`scheduling.py`).
- HTTP: [`apps/api/schema.yml`](../../../apps/api/schema.yml). Frontend: `features/notifications/` (TanStack Query).
- Membership-scoped realtime invalidation (`notification.created` / `notification.updated` / `notification.bulk_updated`) refreshes the list and unread badge; transport is `houston/realtime/` (see [`realtime_domain.md`](realtime_domain.md)).
- Event keys: `houston/notifications/constants.py`.
- Native FCM: `PushDevice` user-scoped; send gated by membership `push_enabled` and `PUSH_V1_EVENT_KEYS`. Web has no push toggle and no service worker. Web Push / VAPID removed.
- Chat push (`chat.message.received`) anti-spam: Redis conversation presence (`chat:presence:{membership_id}:{conversation_id}`, TTL 45s, heartbeat via `POST .../chat/conversations/{id}/presence/`) and push throttle (`push:chat:{conversation_id}:{recipient_membership_id}`, TTL 120s). In-app chat notification rules (dedupe 5 min) are unchanged.

## 3. Out of Scope

- General-purpose email notifications in MVP.
- SMS, WhatsApp, or other external messaging channels.
- Quiet hours, digests, grouping, or presence-aware suppression for non-chat notifications.
- Rich media, attachments, or media binaries inside notifications.
- Notification-based access grants or notification-based business truth.
- Chat sounds and message-body previews in notifications (in-app and native FCM `chat.message.received` use generic copy; message body remains excluded).
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
- Target channel direction is `info` -> `in_app`, `action_required` -> `in_app` and `push`, `urgent` -> `in_app` and `push`, `system` -> `in_app` or selective email depending on type.

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
  - `push` is native FCM; Web Push is out.
  - `email` remains selective unless separately validated.

- `NotificationDelivery`
  - Native FCM: `PushDelivery` per notification + device (`queued`, `processing`, `sent`, `failed`, `skipped`).
  - Email delivery tracking is not implemented.

- `NotificationPreference`
  - Minimal recipient/channel preference such as `push_enabled`.
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

Current code:
- `Notification` model with statuses `unread`, `read`, `archived`.
- In-app notifications plus native FCM `PushDelivery` tracking; email delivery tracking not implemented.

## 7. Permissions

- A user may only list or update their own notifications.
- Notification creation requires recipient eligibility after backend establishment scope and RBAC checks.
- Notification visibility does not grant subject visibility.
- Opening a notification must pass the normal authorized fetch for the target resource.
- Push delivery does not bypass authentication or authorization.
- Role-specific recipient rules depend on adjacent domain rules and notification rules, not on frontend logic.
- Support or admin access to product notifications is not validated as default MVP behavior.

## 8. Triggers

Allowlisted event keys: `LOT1_EVENT_KEYS` in `houston/notifications/constants.py`. Producers: `houston/notifications/scheduling.py`. Do not copy the frozenset here.

Chat `chat.message.received`: generic copy; `subject_type=chat_conversation`; in-app dedupe 5 min; push suppressed when conversation presence is active or within the 2-minute throttle.

No notification for signal aggregation or Action Plan validate / direct-done without validation.

Membership-scoped WS invalidation: `notification.created`, `notification.updated`, `notification.bulk_updated` (`notifications/services.py`).

## 9. HTTP

[`apps/api/schema.yml`](../../../apps/api/schema.yml). Push delivery is native FCM only. Token sync is user-scoped. `push_enabled` remains membership-scoped at send time. General-purpose email notification workflows are not implemented.

## 10. Frontend Expectations

- Notification Center lists the authenticated user's notifications only.
- Frontend must not treat notifications as source of business truth.
- Opening a notification should navigate to a safe route and then refetch the authorized subject through the backend API.
- Chat message notifications (`chat.message.received`): navigate to `/chat/{conversation_id}` (`subject_type=chat_conversation`). Notification copy must not include message body. While viewing a conversation, the client sends presence heartbeats (`POST .../presence/`, ~30s when visible) so the backend can suppress push if it still delivers.
- Comment mention notifications (`comment.mention.created`): when `navigation` is present, open the parent detail (`signal` or `action_plan_execution`) with the Commentaires tab and scroll/highlight the mentioned comment (`?tab=comments&commentId={subject_id}`). When `navigation` is `null` (comment hard-deleted; V1 without denormalized parent on `Notification`), mark read only — no navigation. When the parent loads but the comment is absent from the authorized list, show an inline unavailable message in the Commentaires tab.
- `navigation` is a non-sensitive routing hint (parent type + UUID only); authorization remains on the parent and comment list fetches.
- Native profile exposes `push_enabled` (fail-closed opt-in: OS permission → FCM token → upsert → then PATCH). Web has no push toggle.
- Tap of an OS notification uses payload `url` + `establishment_id` (not the in-app list `url`). Native HTTPS deep-link **handler** is live (`getLaunchUrl` / `appUrlOpen` → `AppRoute`). Verified Play App Links / iOS Universal Links remain store-identity work.
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
- Inspect Signal, Action Plan, Feed, and adjacent product docs before changing notification trigger assumptions.
- Do not make Notification a source of truth.
- Do not grant access through notifications.
- Do not include raw Observation text, complete comment bodies, chat message bodies, media binaries, credentials, auth artifacts, or AI request content in notifications.
- Do not add general-purpose email workflows in MVP unless separately validated.
- Do not notify the actor for their own normal action by default.
- Do not add grouping, digests, quiet hours, or provider-specific push setup to this domain doc unless separately validated.
- When notification APIs change, update backend authorization, OpenAPI, generated clients, tests, and this document together.
