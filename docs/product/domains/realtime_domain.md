# Realtime Domain

Status: authoritative
Implementation status: operational WebSocket invalidation live for Signal, Action Plan, Comment, Notification, and observation-pipeline downstream invalidation. Chat V1 is a separate WS contract under `houston/chat/`.

## 1. Purpose

Realtime owns Houston's live transport boundary for keeping authorized operational screens fresh.

- It owns authenticated connection scope, subscription authorization, minimal message shape, and invalidation/refetch guidance.
- It is a transport and invalidation layer, not Event, not Notification, not Feed, and not authoritative business state.
- It does not own Signal, Action Plan, Comment, Notification, Chat, or Feed lifecycle.

## 2. MVP Scope

- Backend-capable realtime foundation through Django Channels configuration and the `houston.realtime` app.
- Authenticated connection boundary with backend-owned subscription authorization before any establishment, user, or detail scope is joined.
- Minimal non-sensitive invalidation messages only.
- Establishment-scoped operational invalidation for Signal feed/detail, Action Plan catalog/execution surfaces, and execution feed.
- Access/session messages for logout, establishment switch, and membership changes affecting bootstrap or workspace.
- Comment invalidation implemented ; Notification invalidation implemented (membership-scoped broadcast).
- Frontend query invalidation and REST refetch through TanStack Query after relevant realtime messages.
- Safe reconnect behavior: refetch active authorized queries after reconnect or missed delivery.

Current code truth:

- Channels is installed and channel-layer configuration exists.
- `houston/realtime` provides operational WS consumer, ws-ticket REST, broadcast after commit, and access events.
- Operational invalidation is emitted from domain services (Signal lifecycle, Action Plan lifecycle, Comment sync writers, Notification lifecycle writers) and async downstream paths (observation pipeline → `signal.created` / `signal.updated`).
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
- Chat message **send** is HTTP `POST …/messages/` ; WebSocket delivers `message.created` and access/structure events only.

Chat WebSocket delivery must not depend only on conversation groups joined at auth :

- each connection joins a personal membership group `chat_est_{establishment_id}_mbr_{membership_id}` ;
- message broadcast targets participants' personal groups so new DM/groups deliver the first message without reconnect.

Auth stack for Chat WebSocket :

- `OriginValidator(HOUSTON_CLIENT_ORIGINS)` + `URLRouter` ;
- **no** `AuthMiddlewareStack` ;
- ticket REST one-time in first WS message (see [`authentication_charter.md`](../../architecture/authentication_charter.md)).

### Operational WebSocket invalidation (implemented — separate from Chat)

Establishment-scoped invalidation uses `type: "invalidate"` with stable `subject_type` / `reason` pairs. Payload allowlist: `type`, `subject_type`, `reason`, `establishment_id`, `entity_id`, `occurred_at` — never resource bodies or snapshots.

Server message types on the operational socket: `auth.ok` (handshake), `invalidate`, `access`.

Access / session messages use `type: "access"` with reasons: `session.revoked`, `establishment.switched`, `membership.deactivated`, `membership.updated`.

Implemented `invalidate` reasons (verify in domain `services.py` before extending). Machine-readable contract: [`contracts/operational-realtime-invalidation.json`](../../../contracts/operational-realtime-invalidation.json) — keep in sync with this table and emitter parity tests when extending.

| `subject_type` | `reason` | `entity_id` | Emitted today | Frontend surfaces |
|---|---|---|---|---|
| `signal` | `signal.updated` | signal id | yes — sync lifecycle (pin, cancel, resolve, …) | signal feed, signal detail |
| `signal` | `signal.created` | signal id | yes — observation async pipeline | signal feed, signal detail |
| `action_plan` | `action_plan.created` | action plan id | yes — catalog create, one-shot create | action-plans catalog, detail |
| `action_plan` | `action_plan.updated` | action plan id | yes — catalog patch, activate/deactivate | action-plans catalog, detail |
| `action_plan_execution` | `action_plan_execution.created` | action plan execution id | yes — create, catalog use, schedule materialization | action-plan-execution-feed, execution-detail, signals |
| `action_plan_execution` | `action_plan_execution.updated` | action plan execution id | yes — reopen, schedule sync/reactivate, task activity | same as `created` |
| `action_plan_execution` | `action_plan_execution.canceled` | action plan execution id | yes — manual cancel, schedule sync, signal resolve cascade | same as `created` |
| `action_plan_execution` | `action_plan_execution.done` | action plan execution id | yes — mark-done (no validation), validate | same as `created` |
| `action_plan_execution` | `action_plan_execution.pending_validation` | action plan execution id | yes — mark-done when validation required | same as `created` |
| `action_plan_execution_task` | `action_plan_execution_task.updated` | task execution id | yes — mark-done, skip, observation handoff | action-plan-execution-feed, execution-detail prefix, signals |
| `action_plan_assignee` | `action_plan_assignee.updated` | **assignee row id** (not execution id) | yes — materialization structure repair only | execution-detail prefix (establishment-scoped sweep; feed unchanged) |
| `comment` | `comment.signal.created` | signal id | yes — sync signal comment create | signal comment list |
| `comment` | `comment.signal.inherited` | linked action plan execution id | yes — sync signal comment create when execution is linked | execution comment list (inherited signal comments) |
| `comment` | `comment.execution.created` | action plan execution id | yes — sync execution comment create (root or reply) | execution comment list |
| `comment` | `comment.execution.resolved` | action plan execution id | yes — sync execution comment resolve | execution comment list |
| `comment` | `comment.execution.unresolved` | action plan execution id | yes — sync execution comment unresolve | execution comment list |
| `notification` | `notification.created` | notification id | yes — membership-scoped | notification list + badge |
| `notification` | `notification.updated` | notification id | yes — mark-read / archive | notification list + badge |
| `notification` | `notification.bulk_updated` | recipient membership id (bulk) | yes — mark-all-read | notification list + badge |

`notification.bulk_updated` is a membership-level bulk event: `entity_id` is the recipient membership id, not an individual notification id. Delivery uses the membership Channels group (`realtime_est_{establishment_id}_mbr_{membership_id}`), not the establishment-wide invalidation group.

In-app Action Plan notification keys (not WS `reason` values): `action_plan.execution.created`, `.pending_validation`, `.canceled`, `.reopened` — see `LOT1_EVENT_KEYS` in `houston/notifications/constants.py`. No `action_plan.execution.reassigned` — runtime assignee reassignment API does not exist; schedule assignee changes surface via `action_plan_execution.created` / `.canceled`.

Action plan invalidation refreshes `action-plan-execution-feed` and execution-detail queries.

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
- Terminal action plan executions (`done` / `canceled`) disappear from the active Execution Feed through authorized Feed refetch, not realtime local deletion as authority.
- Notifications remain persisted attention messages; operational realtime notification refresh invalidates the recipient's notification list and unread badge via membership-scoped `invalidate` events.
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
- Action Plan — catalog create/update → `action_plan.created`, `action_plan.updated`; execution lifecycle → `action_plan_execution.*`; task updates → `action_plan_execution_task.updated`; assignee repair → `action_plan_assignee.updated`
- Comment — sync create / resolve → `comment.signal.*`, `comment.execution.*` (action plan execution comments)
- Notification — create / read / archive / mark-all-read → membership-scoped `notification.created`, `notification.updated`, `notification.bulk_updated` (emitted from `notifications/services.py`, not domain lifecycle writers)

### Action Plan lifecycle side-effects on Signal (refetch contract)

When an Action Plan execution lifecycle write also mutates a linked Signal, transport depends on the mutation. Signal-linked plan create schedules `signal.updated` when the Signal becomes `in_progress` (and optional unpin). Canceling all linked executions reopens the Signal to `open` and schedules `signal.updated`. When all linked executions are terminal with at least one `done`, mark-done or validate auto-resolves the active linked Signal via `resolve_signal_from_execution_sync` and schedules `signal.updated`. Manual `resolve_signal` (from `open` only) cancels active linked executions and schedules `signal.updated`. See `action_plans/services.py` and `signals/services.py`.

See **Operational WebSocket invalidation** under section 2 for the reason matrix. Chat message transport belongs to [`chat_domain.md`](chat_domain.md).

## 9. HTTP / Channel

HTTP: [`apps/api/schema.yml`](../../../apps/api/schema.yml) (`POST …/realtime/ws-ticket/`). Operational WS: `/ws/v1/establishments/{establishment_id}/realtime/`. Chat WS: [`chat_domain.md`](chat_domain.md). Ticket auth: [`authentication_charter.md`](../../architecture/authentication_charter.md). ASGI in `apps/api/config/asgi.py` (`OriginValidator` + `URLRouter`, no `AuthMiddlewareStack`). Invalidation is establishment-broadcast; access events may target session or membership groups. Machine contract: [`contracts/operational-realtime-invalidation.json`](../../../contracts/operational-realtime-invalidation.json).

## 10. Frontend Expectations

- Frontend treats realtime messages as invalidation/refetch hints, not authoritative state.
- TanStack Query owns server state.
- On relevant message, invalidate or refetch matching query keys and update UI from API responses.
- Frontend must not treat realtime payloads as complete resource state.
- Frontend must not render sensitive business content directly from realtime payloads.
- Frontend must not infer authorization from channel names or local subscription state.
- Feed order, insertion, removal, and filtering remain backend-owned through Feed refetch.
- Open Signal and Action Plan execution detail views refetch when matching operational invalidation messages arrive.
- On reconnect, refetch active signal, action plan, and notification queries that are still visible and authorized (operational provider). Comment lists are not refetched on reconnect — a known limitation; live comment threads still refresh via `comment.*` invalidation during the session.
- Notification Center refetch via realtime is implemented: membership-scoped `notification.created`, `notification.updated`, and `notification.bulk_updated` invalidate `['notifications','list', establishmentId]` (see `apply-operational-invalidation.ts`).
- Comment surfaces refetch via operational `comment` invalidation (implemented).
- Action plan execution surfaces refetch via operational `action_plan_execution.*` invalidation (implemented).
- Chat V1 follows [`chat_domain.md`](chat_domain.md); do not apply generic invalidation-only rules to Chat message WebSocket delivery.
- Operational Signal / Action Plan invalidation follows invalidation/refetch rules in this document.

Current code truth:

- Chat V1 frontend WebSocket client: `apps/web/src/features/chat/` (`useChatWebSocket`, `ChatRealtimeProvider`).
- Operational frontend WebSocket client: `apps/web/src/features/realtime/` (`useOperationalRealtimeWebSocket`, `OperationalRealtimeProvider`, `applyOperationalInvalidation`, `applyRealtimeAccessEvent`).

## 11. AI Agent Notes

- Inspect `houston/realtime/` and domain `services.py` emitters before claiming which `reason` values are live.
- Inspect `apps/api/schema.yml` for the operational ws-ticket route before claiming HTTP surface.
- Inspect Feed documentation before changing feed invalidation behavior.
- Inspect Notification documentation before changing notification refresh behavior.
- Inspect Signal and Action Plan documentation before changing detail invalidation triggers.
- Inspect Comments documentation before changing comment refresh behavior.
- Read [`chat_domain.md`](chat_domain.md) before Chat WebSocket work ; do not implement Chat in `houston/realtime` as a generic platform.
- Inspect RBAC documentation before changing subscription authorization.
- Inspect Security / RGPD documentation before changing payload content or logging.
- Do not make realtime authoritative state.
- Do not make realtime grant access.
- Do not send Observation text/body, comment bodies, media links, signed media links, credentials, or AI request/model-input content in **generic** realtime payloads.
- Do not send chat message bodies outside the Chat V1 WebSocket protocol defined in [`chat_domain.md`](chat_domain.md).
- Do not implement client-side lifecycle mutation based only on realtime payloads.
- Do not claim extra channel names are implemented without code proof.
- When adding new operational invalidation, update domain services, frontend invalidation helpers, tests, and this document together.
