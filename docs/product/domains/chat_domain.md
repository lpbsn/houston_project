# Chat Domain (V1)

Status: authoritative
Last reviewed: 2026-06-09
Implementation status: **implemented_core** (Lots 2–6 done — REST, WS messages, Terrain UI, purge, hardening ; Lot 7 doc alignment)

**Dettes techniques actives** : post-MVP product gaps documented in this domain doc (P0/Lot 6 closed ; group settings UI, bootstrap flag, and related items remain open).

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

- Text only.
- Max 2,000 characters after trim.
- Ordering : `created_at` ascending, then `id`.
- Idempotency via `client_message_id` per `(conversation, author_membership)`.
- **WebSocket is the only message send channel in V1** (no REST message write endpoint).
- Messages are stored in PostgreSQL **before** WebSocket broadcast.
- Hard purge of messages older than 7 days (automatic).

### Access

- Chat is establishment-global : **no** BusinessUnit / ActivitySubject / `MembershipScope` restriction for chat access.
- Available when establishment is `active`, `chat_enabled=True`, and caller has an active membership.
- All active roles may use chat : Owner, Director, Manager, Staff.
- Staff may create DMs ; Staff **cannot** create groups.
- Owner, Director, Manager may create groups.

### Unread (minimal)

- Per-participant unread only ; no read receipts, no delivered status, no typing indicator.
- A conversation is unread for the current membership when :
  - a last message exists ;
  - the last message was not sent by the current membership ;
  - the participant has not marked the conversation seen through `POST .../seen/`.
- Seen state uses `last_seen_message_id` (UUID, **no FK**) + `last_seen_message_created_at` so unread survives message purge.
- **Forbidden** : `ChatMessageRead`, visible read receipts, double-check marks, “vu/lu” UI.

### Realtime (Chat-only)

- Chat V1 uses a **dedicated WebSocket protocol** for live message delivery.
- This is an explicit exception to generic realtime invalidation rules (see [`realtime_domain.md`](realtime_domain.md)).
- WebSocket auth : REST one-time ticket in the first message (see [`authentication_charter.md`](../../architecture/authentication_charter.md)).
- Allowed WS server events in V1 :
  - `message.created`
  - `message.rejected`
  - `access.revoked` (global Chat WS access loss — closes socket)
  - `conversation.access_revoked` (targeted to the affected user only — does **not** close global socket)
- **Not allowed** in V1 : `conversation.updated` broadcast, typing, read/delivered events, notification events.

#### `access.revoked` vs `conversation.access_revoked`

| Event | Meaning | Client behavior |
|-------|---------|-----------------|
| `access.revoked` | Global Chat WS access is no longer valid | Stop auto-reconnect ; close current Chat socket ; purge/invalidate Chat queries |
| `conversation.access_revoked` | Loss of access to one conversation only | Leave active conversation route if needed ; keep socket open |

Supported `access.revoked` `reason` values :

| `reason` | Trigger |
|----------|---------|
| `membership_deactivated` | membership deactivated |
| `session_revoked` | logout / `revoke_session` |
| `establishment_switched` | `switch_selected_establishment` on current `UserSession` |
| `chat_disabled` | `update_establishment_chat_enabled(False)` |
| `access_denied` | `message.send` revalidation failure |

- Backend revalidates session, membership, establishment, organization, `chat_enabled`, and `selected_establishment` before each `message.send`.
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
- Chat notifications, push, sounds, Notification Center integration.
- Read receipts, delivered status, typing indicators, presence.
- `ChatMessageRead` or per-message read APIs.
- REST endpoint to send messages (WS only).
- Attachments, audio, reactions, threads, message search, message edit/delete by users.
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
  - `last_seen_message_id` (UUID, no FK), `last_seen_message_created_at`

- `ChatMessage`
  - `conversation` FK
  - `author_membership` FK
  - `body` (text, max 2000 trimmed)
  - `client_message_id` (UUID, idempotency key)

## 6. Lifecycle / Statuses

- `ChatConversation` : active until group deleted (`deleted_at`) ; DM deleted when involving inactive membership.
- `ChatMessage` : `created` → hard-deleted by purge after 7 days.
- No user message edit/delete in V1.

## 7. Permissions

| Action | Rule |
|--------|------|
| Access chat | Active membership + active establishment + `chat_enabled` |
| Create DM | Any active member ; target = active membership same establishment |
| Create group | Manager, Director, Owner |
| View conversation | Active participant only |
| Send message | Active participant ; WS only ; revalidated on each send |
| Group admin actions | Participant with `admin` role |
| Add/remove/promote participants | Group admin |
| Rename group | Group admin |
| Delete group | **Group admin participant only** (product API) |
| Leave group | Any active member participant |
| Toggle `chat_enabled` | Owner/Director |
| Mark seen | Current participant only ; no broadcast to others |

**Group without admin** : promote oldest remaining Owner/Director participant ; else oldest admin-eligible participant per service rule.

**Support/admin delete outside participation** : management command only ; not product API V1.

## 8. Events

Internal `EventEnvelope` events (payloads without message body):

- `ChatConversationCreated`
- `ChatConversationDeleted`
- `ChatGroupRenamed`
- `ChatParticipantAdded`
- `ChatParticipantRemoved`
- `ChatParticipantPromoted`
- `ChatMessageCreated` (ids only)
- `ChatMessagePurged`
- `ChatConversationSeen` (local participant ; no WS broadcast to others)
- `ChatEnabledForEstablishment` / `ChatDisabledForEstablishment`

**Forbidden** : `ChatMessageRead`, `ChatReadReceiptCreated`, `ChatMessageDelivered`, typing events.

## 9. API / Channel Surface

**HTTP API truth** : [`apps/api/schema.yml`](../../../apps/api/schema.yml) — Chat endpoints under `/api/v1/establishments/{establishment_id}/chat/` are **implemented** (Lots 3–4). Do not assume parity with this doc without checking schema + debt register.

### REST (establishment-scoped, implemented)

All under `/api/v1/establishments/{establishment_id}/chat/` :

- `POST ws-ticket/`
- `GET status/`
- `GET conversations/`
- `POST conversations/dm/`
- `POST conversations/groups/`
- `GET/PATCH/DELETE conversations/{id}/` (delete : admin participant only)
- `GET conversations/{id}/messages/` (read only)
- `POST conversations/{id}/seen/`
- `GET eligible-memberships/`
- Participant management endpoints (add, remove, promote, leave)
- `PATCH settings/` (`chat_enabled` toggle)

**No** `POST conversations/{id}/messages/` in V1.

### WebSocket

- Path : `/ws/v1/establishments/{establishment_id}/chat/`
- Auth : first message `{ "type": "auth", "ticket": "..." }`
- Send : `{ "type": "message.send", "conversation_id", "client_message_id", "body" }`
- ASGI : `AllowedHostsOriginValidator` + `URLRouter` ; **no** `AuthMiddlewareStack`
- Server : Daphne

### Channel groups

- Personal (mandatory) : `chat_est_{establishment_id}_mbr_{membership_id}`
- Session (mandatory for live revocation) : `chat_session_{session_id}`
- Conversation (optional supplement) : `chat_est_{establishment_id}_conv_{conversation_id}`

## 10. Frontend Expectations

- Route `/chat` ; mobile-first Terrain UI (WhatsApp-inspired), not a parallel design system.
- TanStack Query : conversations, messages, eligible-memberships, seen mutations.
- WebSocket : message send + receive ; failed send → local `failed` state → retry after reconnect (WS only).
- Reconnect : new ws-ticket ; refetch conversations and open conversation messages.
- No localStorage/sessionStorage for tokens or chat payloads.
- No read-receipt UI ; minimal unread badge only.
- Show retention notice : messages older than 7 days are automatically deleted.
- Hide chat nav when `chat_enabled=false` or user cannot access.

## 11. AI Agent Notes

- Inspect `apps/api/schema.yml` for the current Chat REST surface (implemented).
- Inspect §1–§10 of this doc for remaining post-core gaps (events, group settings UI, bootstrap flag).
- Inspect [`realtime_domain.md`](realtime_domain.md) for Chat vs global realtime boundary.
- Inspect [`authentication_charter.md`](../../architecture/authentication_charter.md) before WebSocket auth work.
- Inspect [`rbac_permissions_domain.md`](rbac_permissions_domain.md) and [`identity_membership_domain.md`](identity_membership_domain.md) for eligibility.
- Do not implement general establishment chat, REST message send, read receipts, notifications, or Signal/Action links.
- Do not use `AuthMiddlewareStack` for Chat WebSocket.
- Do not rely only on conversation groups joined at auth for message delivery.
- When implementing Chat, update OpenAPI, generated clients, tests, and this document together.

## 12. V1 acceptance criteria (documentation)

Checklist aligned with Chat V1 implementation plan §3.5 — verified **2026-06-09** after Lots 2–6:

- [x] Single active Chat V1 definition (this document + carve-out in [`realtime_domain.md`](realtime_domain.md))
- [x] WebSocket auth = REST one-time ticket ; no `AuthMiddlewareStack` ; Origin validated (`AllowedHostsOriginValidator`)
- [x] Chat realtime separated from deferred global Signal/Action/Notification invalidation
- [x] Chat notifications explicitly out of scope (§3)
- [x] Minimal unread only ; no read receipts ; unread survives purge (`last_seen_message_id` UUID non-FK + `last_seen_message_created_at`)
- [x] Hard purge after 7 days documented and implemented (Celery + management command) ; purge does not break participant seen state
- [x] Message send WebSocket-only ; no REST `POST .../messages/`
- [x] Membership-centric model (`ChatParticipant.membership`, `ChatMessage.author_membership`)
- [x] Participant eligibility and permissions documented (§7) and enforced in backend tests
- [x] REST + WS endpoints present in [`apps/api/schema.yml`](../../../apps/api/schema.yml) and backend `houston/chat/`
- [x] Terrain UI at `/chat` and `/chat/:conversationId` (Lots 5)
- [x] Membership deactivation hook, `conversation.access_revoked`, rate limits (Lot 6)
- [ ] Post-core product gaps tracked in debt register only (group management UI, `chat_enabled` toggle UI, `EventEnvelope`)
