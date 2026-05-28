# Chat Domain

Status: authoritative
Last reviewed: 2026-05-28
Implementation status: not_started

## 1. Purpose

Chat owns Houston's basic establishment-wide general communication space in MVP.

- It owns free-form text conversation for one general chat per establishment.
- It owns chat message creation, authorized reading, and message ordering within that chat.
- It does not own workflow creation, workflow routing, feed projection, comments, notification routing, or generic realtime invalidation.

## 2. MVP Scope

- One general chat per establishment.
- Authenticated active establishment members can read and send messages when backend-authorized.
- Text-only user-authored messages.
- Chat message body max length is 2,000 characters.
- Establishment-scoped message history through authorized API if implemented later.
- Message ordering by `created_at` ascending in conversation view.
- Candidate paginated history and backfill behavior if implemented later.
- Candidate Chat-specific realtime delivery only if separately implemented and authorized.

## 3. Out of Scope

- Direct messages, private chat, or cross-establishment chat.
- Multiple rooms, channels, topics, or user-created chat spaces.
- Threads, reactions, read receipts, typing indicators, or presence.
- Attachments, media, files, audio, photos, forwarding, pinning, or search.
- AI analysis, summarization, moderation, routing, or chat-to-workflow conversion.
- Signal, Action, Checklist, Observation, Feed, Comment, or Notification integration.
- Workflow creation, assignment, escalation, or operational routing from Chat messages.
- Message editing, deletion, moderation, reporting, or retention tooling unless separately validated.

## 4. Core Invariants

- Chat is free-form establishment-wide communication, not a structured workflow surface.
- Chat is intentionally isolated from Observation, Signal, Action, Checklist, Feed, Notification, Comments, Realtime invalidation, and AI in MVP.
- Backend remains the authority for chat access, message creation, and message history.
- Chat access is establishment-scoped and requires authenticated active membership plus backend authorization.
- Chat never grants access to any other resource.
- Chat messages are user-authored text only in MVP.
- Chat message body must be 1 to 2,000 characters after trimming whitespace.
- Backend validation is authoritative for message length.
- Chat does not create, update, resolve, assign, or route Signals, Actions, Checklists, or Observations.
- Chat content must not appear in Feed items.
- Chat content must not be included in notification payloads unless separately validated later.
- Chat content must not be sent to AI in MVP.
- Generic realtime invalidation must not be treated as raw Chat message transport.
- Any future Chat realtime transport must be Chat-specific and separately authorized.

## 5. Main Objects

- `ChatRoom`
  - MVP concept for the establishment general chat.
  - One general room per establishment in MVP.
  - Not user-created in MVP.

- `ChatMessage`
  - User-authored text message inside the establishment general chat.
  - Establishment-scoped and ordered by creation time.

- `ChatParticipant`
  - Active establishment member allowed to access the general chat.
  - Derived from membership and authorization, not manually managed in MVP.

- `ChatMessageAuthor`
  - Authenticated user who created the message.
  - Must be an active authorized member at send time.

- Candidate `ChatMessageDelivery`
  - Candidate realtime delivery concept if Chat-specific transport is added later.
  - Not validated as persisted business truth.

- Candidate `ChatHistoryPage`
  - Candidate paginated history/backfill response.
  - Exact pagination shape is not validated yet.

- Candidate `ChatChannel`
  - Candidate websocket channel for Chat-specific delivery.
  - Separate from generic realtime invalidation channels.

## 6. Lifecycle / Statuses

- ChatRoom has no product lifecycle in MVP; one default general chat exists per establishment.
- `ChatMessage`: `created`

Not validated yet:
- message editing is out of MVP
- message deletion
- delivery or read-status lifecycle

## 7. Permissions

- Chat access is establishment-scoped.
- Reading messages requires authenticated active membership in the establishment plus backend authorization.
- Sending messages requires authenticated active membership in the establishment plus backend authorization.
- Fetching history or older pages must use the same backend authorization boundary as message reads.
- Any future Chat websocket subscription must use the same backend authorization boundary as HTTP read/send access.
- Cross-establishment chat access is forbidden.
- Deactivated members cannot read or send.
- Owner, Director, Manager, and Staff are expected MVP participants only when they are active authorized members.
- Chat does not grant access to Signals, Actions, Checklists, Observations, feeds, or any other operational resource.

## 8. Events

No implemented Chat event contract is validated in current code or in `apps/api/schema.yml`.

Candidate events only:
- `ChatMessageCreated`
- `ChatMessageDeleted`
- `ChatMessageDeliveryFailed`

## 9. API / Channel Surface

Current HTTP API truth is `apps/api/schema.yml`.
Current WebSocket/channel truth is current backend code.

Implemented HTTP endpoints confirmed today:
- none

Implemented channels confirmed today:
- none

Candidate HTTP capabilities only:
- fetch establishment general chat messages
- send establishment general chat message
- fetch older paginated history

Candidate channel only:
- `ChatChannel`
- `EstablishmentGeneralChatChannel`

Current implementation note:
- Current code proves Channels foundation only.
- `apps/api/config/asgi.py` exposes HTTP only.
- No backend `chat` app, chat API route, chat consumer, or chat frontend surface is confirmed today.

## 10. Frontend Expectations

- Chat UI should be a simple establishment-wide general conversation surface.
- Chat must remain visually and behaviorally separate from Signal and Action comments.
- Chat must not appear as a Signal, Action, Checklist, Feed, or Notification feature.
- Frontend must fetch chat history through authorized API when chat APIs exist.
- TanStack Query owns chat history and send-state reconciliation when HTTP APIs exist.
- Frontend must not use websocket payloads as business truth.
- Any future realtime Chat delivery must reconcile with authorized API state after reconnect, failure, or missed delivery.
- Frontend must handle loading, empty, sending, failed-send, reconnecting, and pagination states if those APIs or channels are implemented.
- Frontend should show a character counter or warning near 1,800 characters and block submit above 2,000 characters, while backend remains authoritative.
- Frontend must not create workflows from Chat messages.
- Frontend must not send attachments, media, or Chat content to AI in MVP.
- Frontend must use generated OpenAPI clients only for chat routes that exist in `apps/api/schema.yml`.

## 11. AI Agent Notes

- Inspect current code before claiming Chat models, services, events, endpoints, channels, or frontend surfaces exist.
- Inspect `apps/api/schema.yml` before listing any Chat HTTP API as implemented.
- Inspect `realtime_domain.md` before adding Chat websocket behavior, but do not treat generic invalidation as raw chat protocol.
- Inspect `comments_domain.md` before changing Chat versus Comments boundaries.
- Inspect `notification_domain.md` before adding any Chat notification behavior.
- Inspect `rbac_permissions_domain.md` before changing Chat access assumptions.
- Inspect `security_rgpd_domain.md` before changing content, logging, retention, export, or privacy assumptions.
- Do not connect Chat to Signal, Action, Checklist, Observation, Feed, Notification, Comments, or AI in MVP.
- Do not add message editing in MVP.
- Do not add room management, room activation, room deactivation, or user-created rooms in MVP.
- Do not add direct messages, multiple rooms, threads, reactions, read receipts, typing indicators, presence, attachments, or media unless separately validated.
- Do not increase Chat message max length without updating this document, backend validation, frontend validation, API schema, and tests.
- Do not send Chat content to AI.
- Do not include Chat content in notification payloads unless separately validated.
- Do not claim endpoints or channels are implemented without proof in current code and `apps/api/schema.yml`.
- When Chat APIs or channels are added later, update backend authorization, OpenAPI, generated clients, frontend handling, tests, and this document together.
