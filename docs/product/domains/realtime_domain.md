# Realtime Domain

Status: authoritative
Last reviewed: 2026-05-28
Implementation status: partial foundation only

## 1. Purpose

Realtime owns Houston's live transport boundary for keeping authorized operational screens fresh.

- It owns authenticated connection scope, subscription authorization, minimal message shape, and invalidation/refetch guidance.
- It is a transport and invalidation layer, not Event, not Notification, not Feed, and not authoritative business state.
- It does not own Signal, Action, Checklist, Comment, Notification, Chat, or Feed lifecycle.

## 2. MVP Scope

- Backend-capable realtime foundation through Django Channels configuration and the `houston.realtime` app.
- Authenticated connection boundary with backend-owned subscription authorization before any establishment, user, or detail scope is joined.
- Minimal non-sensitive invalidation messages only.
- Establishment-scoped feed invalidation direction.
- User-scoped execution and notification invalidation direction.
- Detail-scoped invalidation direction for Signal and Action views.
- Candidate checklist and comment invalidation only when those surfaces are implemented.
- Frontend query invalidation and REST refetch through TanStack Query after relevant realtime messages.
- Safe reconnect behavior: refetch active authorized queries after reconnect or missed delivery.

Current code truth:

- Channels is installed and channel-layer configuration exists.
- `houston.realtime` exists as a backend app.
- Partial means infrastructure foundation only; no product realtime behavior is implemented yet.
- No websocket routing, consumers, channel groups, or frontend websocket client are confirmed in current code.
- No realtime-specific HTTP route is confirmed in `apps/api/schema.yml`.

## 3. Out of Scope

- Realtime as a source of business truth.
- Lifecycle mutation or business workflow execution inside realtime consumers.
- Access grants through connection, subscription, channel naming, or message receipt.
- Complete resource snapshots over realtime transport.
- Observation text/body, comment bodies, chat message bodies, media links, signed media links, credentials, or AI request/model-input content in realtime payloads.
- Guaranteed delivery semantics, durable offline queues, or replay as workflow authority.
- Public channels, cross-tenant subscriptions, or bypass of normal API authorization.
- Chat protocol design, typing indicators, read receipts, or other chat-specific behavior unless separately validated under Chat scope later.
- Provider runbooks, scaling architecture, GraphQL subscriptions, or SSE unless separately validated.

## 4. Core Invariants

- Realtime is a hint and invalidation layer, not authoritative state.
- Realtime never grants access.
- Connection and subscription must be authenticated and backend-authorized.
- Realtime stays establishment-, user-, or resource-scoped.
- Payloads are minimal, technical, and non-sensitive.
- `affected_query_keys` are optional invalidation hints only; frontend must not treat them as authorization or complete query truth.
- Full resource state must be fetched through normal authorized APIs.
- Frontend must invalidate or refetch relevant queries after matching realtime messages.
- Missed or dropped realtime delivery must not corrupt business state.
- Reconnect should trigger safe refetch of relevant active queries.
- Feed remains a backend-authorized projection; realtime only helps refresh it.
- Done shared ChecklistExecutions disappear from the active Execution Feed through authorized Feed refetch, not realtime local deletion as authority.
- Notifications remain persisted attention messages; realtime only helps refresh their UI.
- Generic Realtime messages must not transport raw Chat messages; any future Chat realtime protocol belongs to Chat domain.
- Events remain immutable traces; realtime is selective transport around view-changing changes.

Safe payload examples:

- `event_type`
- `subject_type`
- `subject_id`
- `establishment_id`
- `occurred_at`
- `correlation_id`
- candidate `affected_query_keys`

Unsafe payload examples:

- Observation text/body
- complete comment body
- chat message body
- media links or temporary signed media links
- authentication credentials
- AI request or model-input content

## 5. Main Objects

- `RealtimeConnection`
  - Authenticated websocket/session connection for one user.
  - Must not bypass normal auth, RBAC, or establishment scope.

- `RealtimeSubscription`
  - Binding between one connection and one authorized scope.
  - Scope is establishment, user, or resource detail depending on the channel.

- `RealtimeChannel`
  - Authorized subscription target for invalidation and lightweight refresh hints.
  - Implemented names are not validated today; current channel names below remain candidate.

- `RealtimeMessage`
  - Minimal safe payload describing that something changed.
  - Not a complete resource snapshot.

- `RealtimeInvalidation`
  - Trigger or hint that a frontend query or open detail view should refetch.
  - TanStack Query owns the resulting server-state refresh.

- `RealtimeConsumer`
  - Candidate backend transport handler when websocket handling is implemented.
  - Exact class names and modules are not validated in current code.

## 6. Lifecycle / Statuses

Current code does not validate a concrete realtime lifecycle implementation.

Candidate connection lifecycle:

- `connecting`
- `connected`
- `disconnected`
- `reconnecting`
- `unauthorized`

Candidate subscription lifecycle:

- `requested`
- `authorized`
- `rejected`
- `active`
- `removed`

Candidate message handling flow:

- message received
- ignored if unauthorized, stale, or irrelevant
- matching query invalidated
- authorized API data refetched

## 7. Permissions

- A user may open a realtime connection only when authenticated.
- Establishment-scoped subscription requires active membership in that establishment context.
- User-scoped subscription requires the authenticated user to be the intended recipient.
- Detail-scoped subscription requires normal visibility on the target Signal, Action, or later validated resource.
- Realtime delivery must respect tenant isolation, RBAC, and subject visibility.
- Receiving a message does not grant access to the linked subject.
- Opening or refetching after a realtime message must pass the normal API authorization path.
- Frontend must not subscribe to resources it cannot already access.
- Realtime applies authorization before subscription; RBAC remains the policy owner.

## 8. Events

No implemented realtime event contract is confirmed in current code or `apps/api/schema.yml`.

Realtime should consume selected domain/application events and publish transport messages only for view-changing changes. It should not become the primary business-event catalog.

Candidate source event families for invalidation:

- Signal changes such as create, aggregate, status, urgency, pin, or domain updates
- Action changes such as create, assign, accept, pending validation, validate, reopen, or cancel
- Checklist execution changes such as assign, progress, done, or cancel
- Comment-added changes on authorized Signal or Action context
- Notification create, read, or archive changes for the authorized recipient

Candidate transport-level events:

- `RealtimeSubscriptionAccepted`
- `RealtimeSubscriptionRejected`
- `RealtimeMessageQueued`
- `RealtimeMessageDelivered`
- `RealtimeMessageFailed`

Chat message transport, if implemented later, belongs to Chat scope rather than this generic invalidation contract.

## 9. API / Channel Surface

Current HTTP API truth is `apps/api/schema.yml`.
Current WebSocket/channel truth is current backend code.

Implemented HTTP routes confirmed today:

- none for realtime

Implemented channels confirmed today:

- none

Candidate channels only:

- `EstablishmentFeedChannel`
- `UserExecutionChannel`
- `UserNotificationChannel`
- `SignalDetailChannel`
- `ActionDetailChannel`
- candidate `ChecklistExecutionChannel`
- candidate `CommentContextChannel`

Current implementation note:

- Backend settings include Channels and a channel layer.
- `apps/api/config/asgi.py` currently exposes HTTP only.
- No websocket route table, consumer implementation, or confirmed group naming exists in current code.

## 10. Frontend Expectations

- Frontend treats realtime messages as invalidation/refetch hints, not authoritative state.
- TanStack Query owns server state.
- On relevant message, invalidate or refetch matching query keys and update UI from API responses.
- On reconnect, refetch active feed, detail, execution, and notification queries that are still visible and authorized.
- Frontend must not treat realtime payloads as complete resource state.
- Frontend must not render sensitive business content directly from realtime payloads.
- Frontend must not infer authorization from channel names or local subscription state.
- Feed order, insertion, removal, and filtering remain backend-owned through Feed refetch.
- Open Signal and Action detail views should refetch when matching subject messages arrive.
- Notification Center should refetch when matching recipient-scoped notification messages arrive.
- Comment surfaces should refetch only their authorized parent context when later implemented.
- Checklist execution surfaces should refetch through their owning APIs when later implemented.
- If Chat later uses realtime, it should follow Chat-specific rules rather than reuse this document as a message protocol.

Current code truth:

- No frontend websocket client is confirmed in `apps/web/src/`.
- No realtime query invalidation hook is confirmed in current frontend code.

## 11. AI Agent Notes

- Inspect current backend realtime code before claiming consumers, routes, groups, or channel names are implemented.
- Inspect `apps/api/schema.yml` before claiming any realtime HTTP route exists.
- Inspect Feed documentation before changing feed invalidation behavior.
- Inspect Notification documentation before changing notification refresh behavior.
- Inspect Signal, Action, and Checklist documentation before changing detail invalidation triggers.
- Inspect Comments documentation before changing comment refresh behavior.
- Chat domain documentation does not exist today; use active product docs and MVP build-plan boundaries before adding chat transport behavior.
- Inspect RBAC documentation before changing subscription authorization.
- Inspect Security / RGPD documentation before changing payload content or logging.
- Do not make realtime authoritative state.
- Do not make realtime grant access.
- Do not send Observation text/body, comment bodies, chat message bodies, media links, signed media links, credentials, or AI request/model-input content in realtime payloads.
- Do not implement client-side lifecycle mutation based only on realtime payloads.
- Do not claim candidate channels are implemented without code proof.
- When realtime transport is added later, update backend authorization, frontend invalidation hooks, tests, docs, and this document together.
