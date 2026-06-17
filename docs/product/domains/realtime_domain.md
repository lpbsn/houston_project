# Realtime Domain

Status: authoritative
Last reviewed: 2026-06-09
Implementation status: partial foundation only (generic Signal/Action/Notification invalidation not implemented ; Chat V1 WS lives in `houston/chat/` — see Chat V1 section below)

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
- Partial means infrastructure foundation only; **generic** Signal/Action/Notification realtime is not implemented yet.
- Chat V1 WebSocket (routing, consumer, channel groups, frontend client) is implemented under `houston/chat/` — see Chat V1 section below.
- No **generic** realtime-specific HTTP route is confirmed in `apps/api/schema.yml`.

### Chat V1 realtime (separate contract — see [`chat_domain.md`](chat_domain.md))

Chat V1 is implemented **before** generic Signal/Action/Notification realtime invalidation.

- Chat uses its own WebSocket path, ticket auth, and message protocol under `houston/chat/`.
- Chat V1 realtime is **messages-only** over WebSocket : `message.created`, `message.rejected`, plus targeted `conversation.access_revoked`.
- Chat message text may be transported over WebSocket **only** to authorized active participants of that conversation.
- Chat V1 is **not** generic invalidation/refetch ; it is live message delivery with PostgreSQL as persisted truth.
- REST remains authoritative for conversation structure, history, participants, seen state, and ws-ticket issuance.
- **No REST message send in V1** ; WebSocket is the only write channel for messages.

Chat WebSocket delivery must not depend only on conversation groups joined at auth :

- each connection joins a personal membership group `chat_est_{establishment_id}_mbr_{membership_id}` ;
- message broadcast targets participants' personal groups so new DM/groups deliver the first message without reconnect.

Auth stack for Chat WebSocket :

- `AllowedHostsOriginValidator` + `URLRouter` ;
- **no** `AuthMiddlewareStack` ;
- ticket REST one-time in first WS message (see [`authentication_charter.md`](../../architecture/authentication_charter.md)).

### Global realtime invalidation (deferred — post Chat V1)

Future phases may add lightweight invalidation for Signal Feed, Execution Feed, notifications, and detail views. That work follows the rules in sections 3–4 below and must not reuse the Chat message protocol.

## 3. Out of Scope

- Realtime as a source of business truth.
- Lifecycle mutation or business workflow execution inside realtime consumers.
- Access grants through connection, subscription, channel naming, or message receipt.
- Complete resource snapshots over realtime transport.
- Observation text/body, comment bodies, media links, signed media links, credentials, or AI request/model-input content in **generic** realtime invalidation payloads.
- Chat message bodies in **generic** invalidation channels (Chat V1 has its own scoped exception — see Chat V1 section above and [`chat_domain.md`](chat_domain.md)).
- Guaranteed delivery semantics, durable offline queues, or replay as workflow authority.
- Public channels, cross-tenant subscriptions, or bypass of normal API authorization.
- Chat protocol implementation in `houston/realtime` as a generic framework (Chat lives in `houston/chat/`).
- Chat typing indicators, read receipts, delivered status, or notification routing (see [`chat_domain.md`](chat_domain.md) out of scope).
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
- Terminal checklist executions (`done` / `canceled`) disappear from the active Execution Feed through authorized Feed refetch, not realtime local deletion as authority.
- Notifications remain persisted attention messages; realtime only helps refresh their UI.
- Generic Realtime invalidation must not transport raw Chat messages.
- Chat V1 message transport is defined only in [`chat_domain.md`](chat_domain.md) and is not a precedent for generic invalidation payloads.
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
- chat message body (in generic invalidation payloads; Chat V1 scoped exception applies only in Chat WS protocol)
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

Chat message transport is implemented in `houston/chat/` and belongs to Chat scope only — not this generic invalidation contract.

## 9. API / Channel Surface

Current HTTP API truth is `apps/api/schema.yml`.
Current WebSocket/channel truth is current backend code.

**Chat V1 WebSocket** (implemented — see [`chat_domain.md`](chat_domain.md)):

- Path : `/ws/v1/establishments/{establishment_id}/chat/`
- App : `houston/chat/` (consumer, routing, ws-ticket REST)
- Not part of generic invalidation channels below

Implemented HTTP routes confirmed today (generic realtime):

- none for realtime

Implemented channels confirmed today (generic realtime):

- none

Candidate channels only:

- `EstablishmentFeedChannel`
- `UserExecutionChannel`
- `UserNotificationChannel`
- `SignalDetailChannel`
- `ActionDetailChannel`
- candidate `ChecklistExecutionChannel`
- candidate `CommentContextChannel`

Current implementation note (generic realtime):

- Backend settings include Channels and a channel layer.
- `apps/api/config/asgi.py` exposes HTTP and **Chat V1 WebSocket** (`AllowedHostsOriginValidator` + `houston/chat/` routing).
- **Generic** invalidation websocket routes, consumers, and channel groups are not implemented in `houston/realtime/`.

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
- Chat V1 follows [`chat_domain.md`](chat_domain.md) ; do not apply generic invalidation-only rules to Chat message WebSocket delivery.
- Global Signal/Action/Notification realtime (when implemented) follows invalidation/refetch rules in this document.

Current code truth:

- Chat V1 frontend WebSocket client exists in `apps/web/src/features/chat/` (`useChatWebSocket`, `ChatRealtimeProvider`).
- No **generic** Signal/Action/Notification realtime query invalidation hook is confirmed in current frontend code.

## 11. AI Agent Notes

- Inspect current backend realtime code before claiming consumers, routes, groups, or channel names are implemented.
- Inspect `apps/api/schema.yml` before claiming any realtime HTTP route exists.
- Inspect Feed documentation before changing feed invalidation behavior.
- Inspect Notification documentation before changing notification refresh behavior.
- Inspect Signal, Action, and Checklist documentation before changing detail invalidation triggers.
- Inspect Comments documentation before changing comment refresh behavior.
- Read [`chat_domain.md`](chat_domain.md) before Chat WebSocket work ; do not implement Chat in `houston/realtime` as a generic platform.
- Inspect RBAC documentation before changing subscription authorization.
- Inspect Security / RGPD documentation before changing payload content or logging.
- Do not make realtime authoritative state.
- Do not make realtime grant access.
- Do not send Observation text/body, comment bodies, media links, signed media links, credentials, or AI request/model-input content in **generic** realtime payloads.
- Do not send chat message bodies outside the Chat V1 WebSocket protocol defined in [`chat_domain.md`](chat_domain.md).
- Do not implement client-side lifecycle mutation based only on realtime payloads.
- Do not claim candidate channels are implemented without code proof.
- When realtime transport is added later, update backend authorization, frontend invalidation hooks, tests, docs, and this document together.
