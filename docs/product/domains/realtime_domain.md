# Realtime Domain

Status: authoritative
Last reviewed: 2026-06-20
Implementation status: operational WebSocket invalidation implemented for Signal, Action, and Checklist (templates / assignments / executions) ; access/session handlers implemented ; Chat V1 remains a separate WS contract under `houston/chat/`. Comments, Notifications, and async observation-pipeline invalidation are not implemented.

## 1. Purpose

Realtime owns Houston's live transport boundary for keeping authorized operational screens fresh.

- It owns authenticated connection scope, subscription authorization, minimal message shape, and invalidation/refetch guidance.
- It is a transport and invalidation layer, not Event, not Notification, not Feed, and not authoritative business state.
- It does not own Signal, Action, Checklist, Comment, Notification, Chat, or Feed lifecycle.

## 2. MVP Scope

- Backend-capable realtime foundation through Django Channels configuration and the `houston.realtime` app.
- Authenticated connection boundary with backend-owned subscription authorization before any establishment, user, or detail scope is joined.
- Minimal non-sensitive invalidation messages only.
- Establishment-scoped operational invalidation for Signal feed/detail, Action execution-feed/detail, and Checklist templates / assignments / execution detail / execution feed.
- Access/session messages for logout, establishment switch, and membership changes affecting bootstrap or workspace.
- Comment and Notification invalidation not implemented.
- Frontend query invalidation and REST refetch through TanStack Query after relevant realtime messages.
- Safe reconnect behavior: refetch active authorized queries after reconnect or missed delivery.

Current code truth:

- Channels is installed and channel-layer configuration exists.
- `houston/realtime` provides operational WS consumer, ws-ticket REST, broadcast after commit, and access events.
- Operational invalidation is emitted from domain services (Signal lifecycle, Action lifecycle, Checklist sync writers) — not from Celery materialization or observation async pipeline.
- Chat V1 WebSocket is implemented under `houston/chat/` — see Chat V1 section below.
- Operational REST ws-ticket: `POST /api/v1/establishments/{establishment_id}/realtime/ws-ticket/` (see `apps/api/schema.yml`).
- Operational WS path: `/ws/v1/establishments/{establishment_id}/realtime/`.
- Frontend operational client: `apps/web/src/features/realtime/` (`OperationalRealtimeProvider`, `applyOperationalInvalidation`, `applyRealtimeAccessEvent`).

### Chat V1 realtime (separate contract — see [`chat_domain.md`](chat_domain.md))

Chat V1 is a **separate** WebSocket contract from operational invalidation (same ASGI stack, different path and protocol).

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

### Operational WebSocket invalidation (implemented — separate from Chat)

Establishment-scoped invalidation uses `type: "invalidate"` with stable `subject_type` / `reason` pairs. Payload allowlist: `type`, `subject_type`, `reason`, `establishment_id`, `entity_id`, `occurred_at` — never resource bodies or snapshots.

Server message types on the operational socket: `auth.ok` (handshake), `invalidate`, `access`.

Access / session messages use `type: "access"` with reasons: `session.revoked`, `establishment.switched`, `membership.deactivated`, `membership.updated`.

Implemented `invalidate` reasons (verify in domain `services.py` before extending):

| `subject_type` | `reason` | `entity_id` | Emitted today | Frontend surfaces |
|---|---|---|---|---|
| `signal` | `signal.updated` | signal id | yes — sync lifecycle (pin, urgency, cancel, resolve, …) | signal feed, signal detail |
| `signal` | `signal.created` | signal id | yes — observation async pipeline | signal feed, signal detail |
| `action` | `action.created` | action id | yes | action execution-feed, action detail, signal queries |
| `action` | `action.updated` | action id | yes | same as `action.created` |
| `checklist` | `checklist.updated` | checklist template id | yes — sync template / assignment writers | templates, template detail, assignments, execution-detail prefix, execution feed |
| `execution` | `execution.created` | checklist execution id | yes — sync execution creation and async/read-path materialization | execution detail, checklist mutation surfaces, execution feed |
| `execution` | `execution.updated` | checklist execution id | yes — cancel, task done/skip, observation-from-task handoff | same as `execution.created` |
| `comment` | `comment.signal.created` | signal id | yes — sync signal comment create | signal comment list |
| `comment` | `comment.signal.inherited` | linked action id | yes — sync signal comment create when action is linked | action comment list (inherited signal comments) |
| `comment` | `comment.action.created` | action id | yes — sync action comment create (root or reply) | action comment list |
| `comment` | `comment.action.resolved` | action id | yes — sync action comment resolve | action comment list |
| `comment` | `comment.action.unresolved` | action id | yes — sync action comment unresolve | action comment list |
| `notification` | — | — | **no** | — |

`execution.updated` includes sync checklist task transitions that change execution detail and may start or complete an execution visible on the execution feed.

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
- `affected_query_keys` are not used in operational V1 payloads; frontend dispatches by `subject_type` / `reason` via shared invalidation helpers.
- Full resource state must be fetched through normal authorized APIs.
- Frontend must invalidate or refetch relevant queries after matching realtime messages.
- Missed or dropped realtime delivery must not corrupt business state.
- Reconnect should trigger safe refetch of relevant active queries.
- Feed remains a backend-authorized projection; realtime only helps refresh it.
- Terminal checklist executions (`done` / `canceled`) disappear from the active Execution Feed through authorized Feed refetch, not realtime local deletion as authority.
- Notifications remain persisted attention messages; operational realtime notification refresh is not implemented.
- Generic Realtime invalidation must not transport raw Chat messages.
- Chat V1 message transport is defined only in [`chat_domain.md`](chat_domain.md) and is not a precedent for generic invalidation payloads.
- Events remain immutable traces; realtime is selective transport around view-changing changes.

Safe payload fields (operational `invalidate` — implemented allowlist):

- `type` (`invalidate`)
- `subject_type`
- `reason`
- `establishment_id`
- `entity_id`
- `occurred_at`

Candidate fields not used in operational V1 payloads:

- `correlation_id`
- `affected_query_keys`

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
  - Operational groups: `realtime_est_{establishment_id}` (invalidation broadcast), plus session/membership groups for access events (see `houston/realtime/groups.py`).

- `RealtimeMessage`
  - Minimal safe payload describing that something changed.
  - Not a complete resource snapshot.

- `RealtimeInvalidation`
  - Trigger or hint that a frontend query or open detail view should refetch.
  - TanStack Query owns the resulting server-state refresh.

- `RealtimeConsumer`
  - Operational WebSocket handler: `houston/realtime/consumers.py` (`RealtimeConsumer`).

## 6. Lifecycle / Statuses

Frontend operational connection status (implemented in `apps/web/src/features/realtime/types.ts`):

- `idle`
- `connecting`
- `connected`
- `reconnecting`
- `disconnected`

Candidate subscription lifecycle (not exposed as a separate product model):

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

Operational WebSocket contract is implemented in `houston/realtime/` (payload builders in `ws_payloads.py`, emission via `broadcast.schedule_establishment_invalidation` / `schedule_access_event` after commit).

Domain services publish transport messages for view-changing sync writes. Realtime is not the primary business-event catalog.

Source domains with invalidation emission today:

- Signal — sync lifecycle → `signal.updated`; observation async pipeline → `signal.created`, `signal.updated`
- Action — create and lifecycle → `action.created`, `action.updated`
- Checklist — sync template / assignment writers → `checklist.updated`; execution writers (sync + async materialization) → `execution.created`, `execution.updated`
- Comment — sync create / resolve → `comment.signal.*`, `comment.action.*`

Not emitted today:

- Notification create / read / archive

See **Operational WebSocket invalidation** under section 2 for the reason matrix.

Candidate transport-level events (internal / not product WS types):

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

**Operational WebSocket** (implemented — invalidation/refetch only):

- Path : `/ws/v1/establishments/{establishment_id}/realtime/`
- REST ticket : `POST /api/v1/establishments/{establishment_id}/realtime/ws-ticket/`
- App : `houston/realtime/` (consumer, routing, ws-ticket, broadcast)
- Channel group (invalidation) : `realtime_est_{establishment_id}`

Implemented HTTP routes (operational realtime):

- `POST /api/v1/establishments/{establishment_id}/realtime/ws-ticket/`

Implemented WebSocket routes (operational realtime):

- `/ws/v1/establishments/{establishment_id}/realtime/`

Not implemented (operational):

- Notification-scoped invalidation channels
- Per-resource detail channels (detail refresh uses establishment-scoped invalidation + TanStack Query prefixes)

Candidate channels (not implemented — historical naming):

- `EstablishmentFeedChannel`
- `UserExecutionChannel`
- `UserNotificationChannel`
- `SignalDetailChannel`
- `ActionDetailChannel`
- candidate `ChecklistExecutionChannel`
- candidate `CommentContextChannel`

Current implementation note (operational realtime):

- `apps/api/config/asgi.py` merges Chat V1 and operational realtime WebSocket routing (`AllowedHostsOriginValidator` + `URLRouter`).
- Invalidation is establishment-broadcast; access events may target session or membership groups.

## 10. Frontend Expectations

- Frontend treats realtime messages as invalidation/refetch hints, not authoritative state.
- TanStack Query owns server state.
- On relevant message, invalidate or refetch matching query keys and update UI from API responses.
- Frontend must not treat realtime payloads as complete resource state.
- Frontend must not render sensitive business content directly from realtime payloads.
- Frontend must not infer authorization from channel names or local subscription state.
- Feed order, insertion, removal, and filtering remain backend-owned through Feed refetch.
- Open Signal and Action detail views refetch when matching operational invalidation messages arrive.
- On reconnect, refetch active signal, action, and checklist queries that are still visible and authorized (operational provider).
- Notification Center refetch via realtime not implemented.
- Comment surfaces refetch via operational realtime not implemented.
- Checklist execution surfaces refetch via operational `execution` / `checklist` invalidation (implemented).
- Chat V1 follows [`chat_domain.md`](chat_domain.md) ; do not apply generic invalidation-only rules to Chat message WebSocket delivery.
- Operational Signal / Action / Checklist invalidation follows invalidation/refetch rules in this document.

Current code truth:

- Chat V1 frontend WebSocket client: `apps/web/src/features/chat/` (`useChatWebSocket`, `ChatRealtimeProvider`).
- Operational frontend WebSocket client: `apps/web/src/features/realtime/` (`useOperationalRealtimeWebSocket`, `OperationalRealtimeProvider`, `applyOperationalInvalidation`, `applyRealtimeAccessEvent`).

## 11. AI Agent Notes

- Inspect `houston/realtime/` and domain `services.py` emitters before claiming which `reason` values are live.
- Inspect `apps/api/schema.yml` for the operational ws-ticket route before claiming HTTP surface.
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
- Do not claim candidate channel names (section 9) are implemented without code proof.
- Do not claim `signal.created`, comment, or notification invalidation is live unless domain emitters exist.
- When adding new operational invalidation, update domain services, frontend invalidation helpers, tests, and this document together.
