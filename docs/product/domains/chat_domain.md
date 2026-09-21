# Chat Domain (V1)

Status: authoritative
Last reviewed: 2026-09-21
Implementation status: implemented (REST, WS messages, Terrain UI, purge, conversation/member admin)

Open product gaps: some bootstrap hints; see current_state.

## 1. Purpose

Chat V1 owns establishment-scoped free-form text communication between active members.

- It owns **direct messages (DM)** and **free groups** inside one establishment.
- It owns conversation structure, participant management, message persistence, minimal unread state, and Chat-specific WebSocket message delivery.
- It does **not** own workflow creation, Signal/Action/Observation/Checklist routing, feed projection, comments, notifications, generic realtime invalidation, or AI analysis.

Chat V1 is **not** a single establishment-wide general chat room.

## 2. V1 Scope

### Conversations

- **DM** : unique conversation between two active `EstablishmentMembership` rows in the same establishment.
  - Reopening an existing DM reuses the same conversation.
- **Free groups** : user-created groups with a title and explicit participants.
  - No system/official groups in V1.
- Conversations may remain after all messages are purged (empty conversation shell allowed).

### Messages

- Text, optional reply-to, structured mentions by Unicode code-point offsets, and attachments (`image` / `document`).
- A valid message has a non-empty trimmed `body` **or** at least one validated attachment.
- Max 2,000 characters after trim.
- Ordering : `created_at` ascending, then `id`.
- Idempotency via `client_message_id` per `(conversation, author_membership)`. Retry `POST` returns the existing message (`created=false`) without a second WS fan-out or `chat.message.received` notification.
- **HTTP `POST …/messages/` is the only send command.** WebSocket is events only (`message.created`, access/structure events). A `message.send` frame is a protocol error (close, no persist).
- Fan-out `message.created` and notification only when `created=true`, and only `transaction.on_commit`.
- Hard purge of messages older than **30** days (automatic ; `HOUSTON_CHAT_MESSAGE_RETENTION_DAYS`).

### Access

- Chat is establishment-global : **no** BusinessUnit / ActivitySubject / `MembershipScope` restriction for chat access.
- Available when establishment is `active`, `chat_enabled=True`, and caller has an active membership.
- All active roles may use chat : Owner, Director, Manager, Staff.
- Staff may create DMs ; Staff **cannot** create groups.
- Owner, Director, Manager may create groups.

### Unread (minimal)

- Per-participant unread only ; no read receipts, no delivered status, no typing indicator.
- Conversation list items expose `unread_count` : SQL `COUNT` of messages from **other** memberships strictly after the participant read cursor (`last_seen_message_id` + `last_seen_message_created_at`).
- `unread` on list items is derived server-side as `unread_count > 0` (single source of truth for the boolean).
- Seen state uses `last_seen_message_id` (UUID, **no FK**) + `last_seen_message_created_at` so unread survives message purge.
- Client realtime cache may increment `unread_count` optimistically on `message.created` ; reset happens only after `POST .../seen/` succeeds and the conversations list refetches.
- **Forbidden** : `ChatMessageRead`, visible read receipts, double-check marks, “vu/lu” UI.

### Realtime (Chat-only)

- Chat V1 uses a **dedicated WebSocket protocol** for live message delivery.
- This is an explicit exception to generic realtime invalidation rules (see [`realtime_domain.md`](realtime_domain.md)).
- WebSocket auth : REST one-time ticket in the first message (see [`authentication_charter.md`](../../architecture/authentication_charter.md)).
- Allowed WS server events in V1 :
  - `message.created`
  - `message.rejected` (legacy send-path errors ; send failures are HTTP now)
  - `access.revoked` (global Chat WS access loss — closes socket)
  - `conversation.access_revoked` (targeted to the affected user only — does **not** close global socket)
  - `conversation.updated` (structure invalidation hint after add/promote/remove/leave — to remaining active participants only ; `{ conversation_id }` only ; no sensitive payload)
- **Not allowed** in V1 : typing, read/delivered events, notification events.

#### `access.revoked` vs `conversation.access_revoked` vs `conversation.updated`

| Event | Meaning | Client behavior |
|-------|---------|-----------------|
| `access.revoked` | Global Chat WS access is no longer valid | Stop auto-reconnect ; close current Chat socket ; purge/invalidate Chat queries |
| `conversation.access_revoked` | Loss of access to one conversation only | Leave active conversation route if needed ; keep socket open |
| `conversation.updated` | Conversation structure changed (add/promote/remove/leave) for remaining actives | Invalidate conversation list + detail for that id ; keep socket open |

Supported `access.revoked` `reason` values :

| `reason` | Trigger |
|----------|---------|
| `membership_deactivated` | membership deactivated |
| `session_revoked` | logout / `revoke_session` |
| `establishment_switched` | `switch_selected_establishment` on current `UserSession` |
| `chat_disabled` | `update_establishment_chat_enabled(False)` |
| `access_denied` | live WS revalidation failure |

- Backend revalidates session (`refresh_expires_at` and `absolute_expires_at`), membership, establishment, organization, `chat_enabled`, and `selected_establishment` on Chat WS auth, before each supported client application frame, and before delivering `message.created` / `conversation.updated` / `conversation.access_revoked`.
- Unsupported or invalid client frame types after `auth.ok` are rejected as protocol errors without a PostgreSQL revalidation.
- `message.created` and `conversation.updated` also require an active conversation participant (`get_active_participant`) ; otherwise the body is dropped and the global socket stays open.
- `conversation.access_revoked` is still delivered when global Chat access holds, including to the member who just lost that conversation.
- On revalidation failure : send `access.revoked`, close socket, do **not** create `ChatMessage`.
- Client must not auto-reconnect after `access.revoked` ; network reconnect remains normal for other close reasons.
- `session_revoked` : frontend clears auth/cache and lets auth/bootstrap/login flow resume (no redirect to `/reporting`).

### WebSocket delivery — new conversations while connected

- Do not rely only on conversation groups joined at auth time.
- Each authenticated connection joins a **personal membership group** :
  - `chat_est_{establishment_id}_mbr_{membership_id}`
- Each authenticated connection also joins a **session group** for live access revocation :
  - `chat_session_{session_id}` (scoped to the REST `UserSession` that issued the ws-ticket)
- Message broadcast targets each active participant's personal group so a connected member receives the first message of a newly created DM/group **without reconnecting**.
- Optional conversation groups may be joined dynamically when a participant is added ; personal-group delivery remains mandatory.

### Establishment flag

- `Establishment.chat_enabled` : `True` by default when establishment becomes `active`.
- Data migration sets `chat_enabled=True` for existing active establishments.
- Owner/Director may disable chat for the establishment.

## 3. Out of Scope (V1)

- Single establishment-wide general chat room.
- Chat push, sounds, presence-aware notification suppression.
- Read receipts, delivered status, typing indicators, presence.
- `ChatMessageRead` or per-message read APIs.
- Message send over WebSocket (`message.send` is a protocol error). HTTP `POST …/messages/` is the only send command.
- Audio, reactions, threads, message search, message edit/delete by users.
- Link to Signal, Action, Observation, Checklist, Comments, Feed, AI pipeline.
- Cross-establishment chat.
- Owner/Director reading conversations they do not participate in.
- Owner/Director deleting groups they do not participate in via product API.
- Groups tied to BusinessUnit / ActivitySubject / `MembershipScope`.
- Polling as a continuous message transport.

## 4. Core Invariants

- **Membership-centric model** : `ChatParticipant.membership` and `ChatMessage.author_membership` are authoritative ; API may expose derived user display fields only.
- Backend owns access, conversation rules, message validation, purge, and unread.
- Chat never grants access to operational resources (Signals, Actions, etc.).
- Participant-only visibility : only active participants can read a conversation ; Owner/Director have **no** read access outside participation.
- Cross-establishment access is forbidden.
- Inactive, suspended, invited, or deactivated members are not eligible.
- When a membership becomes inactive :
  - remove from groups (`left_at` set) ;
  - **delete DM conversations entirely** if they involve that membership ;
  - keep group conversations but remove the participant ;
  - preserve their messages until hard purge.
- Chat content must not appear in Feed items or notification payloads in V1.
- Chat content must not be sent to AI in V1.
- Chat message bodies may appear in WebSocket payloads **only** to authorized active participants of that conversation.
- Chat message bodies must not appear in standard technical logs.
- PostgreSQL is message truth ; Redis is not business truth.

## 5. Main Objects

- `ChatConversation`
  - `type` : `dm` | `group`
  - `establishment` FK
  - DM : canonical pair `dm_membership_a`, `dm_membership_b` (sorted membership IDs)
  - Group : `title`, `created_by_membership`
  - `last_message_at` for list sorting
  - `deleted_at` for group soft-delete

- `ChatParticipant`
  - `conversation` FK
  - `membership` FK (`EstablishmentMembership`) — **primary reference**
  - `role` : `member` | `admin`
  - `joined_at`, `left_at` (active when `left_at IS NULL`)
  - `pinned_at` — personal pin (nullable)
  - `history_cutoff_at` — personal DM history cutoff ; messages with `created_at <= cutoff` are invisible to this participant
  - `list_hidden_at` — personal DM list hide ; cleared when a newer message arrives (`list_hidden_at < message.created_at`) or on manual DM reopen via `create_or_get_dm`
  - `last_seen_message_id` (UUID, no FK), `last_seen_message_created_at`

- `ChatMessage`
  - `conversation` FK
  - `author_membership` FK
  - `body` (text, max 2000 trimmed, `blank=True` for later attachment-only messages)
  - `client_message_id` (UUID, idempotency key)
  - `reply_to_id` (UUID, **no FK**) ; parent must exist in the same conversation at send time
  - `ChatMessageMention` : `(membership_id, start, end)` half-open Unicode offsets on the stored trimmed body ; unique `(message, start)`

## 6. Lifecycle / Statuses

- `ChatConversation` : active until group deleted (`deleted_at`) ; DM deleted when involving inactive membership.
- `ChatMessage` : `created` → hard-deleted by purge after 30 days.
- No user message edit/delete in V1.

## 7. Permissions

| Action | Rule |
|--------|------|
| Access chat | Active membership + active establishment + `chat_enabled` |
| Create DM | Any active member ; target = active membership same establishment |
| Create group | Manager, Director, Owner |
| View conversation | Active participant only |
| Send message | Active participant ; HTTP `POST …/messages/` ; same authz as GET messages |
| Group admin actions | Participant with `admin` role |
| Add/remove/promote participants | Group admin |
| Rename group | Group admin |
| Delete group | **Group admin participant only** (product API) |
| Leave group | Any active member participant ; schedules `conversation.access_revoked` (`participant_left`) ; clears personal pin |
| Pin / unpin conversation | Any active participant (personal) |
| Hide DM | Active DM participant only ; marks related unread chat notifications as read ; does not affect peer |
| Toggle `chat_enabled` | Owner/Director |
| Mark seen | Current participant only ; advances cursor on last **visible** message (respects `history_cutoff_at`) ; no broadcast to others |

**Group without admin** : promote oldest remaining Owner/Director participant ; else oldest admin-eligible participant per service rule.

**Support/admin delete outside participation** : management command only ; not product API V1.

## 8. HTTP / WebSocket

HTTP: [`apps/api/schema.yml`](../../../apps/api/schema.yml) under `/api/v1/establishments/{establishment_id}/chat/`. WebSocket path `/ws/v1/establishments/{establishment_id}/chat/`. Ticket auth: [`authentication_charter.md`](../../architecture/authentication_charter.md). Client application frames do not persist messages.

Channel groups: personal `chat_est_{establishment_id}_mbr_{membership_id}`; session `chat_session_{session_id}`; optional conversation group.

## 9. Frontend Expectations

- Route `/chat` ; mobile-first Terrain UI (WhatsApp-inspired), not a parallel design system.
- TanStack Query : conversations, messages, eligible-memberships, seen mutations.
- Group detail (`/chat/:id`) : when `can_manage`, show « Gérer les membres » (add/remove multi-select sequential ops with partial-failure summary ; promote with confirm).
- WebSocket : live receive + banner. Composer send is HTTP and remains usable if WS is down.
- On `conversation.updated` : invalidate conversations list + that conversation detail.
- Reconnect : new ws-ticket ; refetch conversations and open conversation messages.
- No localStorage/sessionStorage for tokens or chat payloads. Chat send drafts and attachment bytes may persist in a dedicated outbox (IndexedDB / Capacitor Data), purged on success, cancel, TTL, logout, switch, and access revocation.
- No read-receipt UI ; minimal unread badge only.
- Show retention notice : messages older than 30 days are automatically deleted.
- Hide chat nav when `chat_enabled=false` or user cannot access.

## 10. Agent notes

- Inspect `apps/api/schema.yml` for the current Chat REST surface (implemented).
- Inspect §1–§10 of this doc for remaining post-core gaps.
- Inspect [`realtime_domain.md`](realtime_domain.md) for Chat vs global realtime boundary.
- Inspect [`authentication_charter.md`](../../architecture/authentication_charter.md) before WebSocket auth work.
- Inspect [`rbac_permissions_domain.md`](rbac_permissions_domain.md) and [`identity_membership_domain.md`](identity_membership_domain.md) for eligibility.
- Do not implement general establishment chat, read receipts, mention-specific push, or Signal/Action links.
- Do not use `AuthMiddlewareStack` for Chat WebSocket.
- Do not rely only on conversation groups joined at auth for message delivery.
- When implementing Chat, update OpenAPI, generated clients, tests, and this document together.
