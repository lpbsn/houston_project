# Comments Domain — Signal & Action Plan Execution Comments

Status: authoritative
Last reviewed: 2026-09-21

Implementation status: implemented (REST threads, mentions, realtime invalidation)

## 1. Purpose

Houston comments allow field and operational teams to add contextual written notes directly inside a Signal or an Action Plan execution.

A comment is not a chat message.
A comment belongs to a business object context:
- Signal
- Action Plan execution

Comments are used to clarify, document, or coordinate around an operational item without changing its lifecycle, classification, assignment, or validation state.

## 2. Product scope V1

V1 supports:

- List comments on a Signal.
- Add a comment on a Signal.
- List comments on an Action Plan execution.
- Add a comment on an Action Plan execution.
- Resolve / unresolve root comments on an Action Plan execution.
- Display comment author.
- Display comment creation date/time.
- Display comments from oldest at the top to newest at the bottom.
- Mention active users of the same establishment with `@`.
- Display inherited Signal comments inside linked Action Plan executions.
- Live refresh of comment lists via operational WebSocket **invalidation** (authorized refetch after `comment.*` messages — no comment body on the socket). See [`realtime_domain.md`](realtime_domain.md) and §9.

V1 does not support:

- Chat behavior.
- Comment edit / delete.
- Comment reactions.
- Comment attachments.
- Comment moderation.
- Offline mutation queue.
- AI processing of comments.

## 3. Core product rules

### 3.1 Signal comments

A Signal comment is created from the Signal detail page.

A Signal comment is stored once.

If the Signal has linked Action Plan executions, the Signal comment is visible inside every linked execution detail timeline.

Signal comments are inherited by linked Action Plan executions for visibility only. They must not be physically duplicated onto each execution.

A Signal comment never changes:
- Signal classification.
- Signal status.
- Signal urgency.
- Signal responsible Business Unit.
- Signal affected Business Unit.
- Linked Action Plan executions.

### 3.2 Action Plan execution comments

An execution comment is created from the Action Plan execution detail page.

An execution comment belongs only to that Action Plan execution.

An execution comment is not visible on the parent Signal.

An execution comment is not visible on other executions linked to the same Signal.

An execution comment never changes:
- Execution status.
- Execution assignment.
- Execution due date / schedule.
- Execution validation state.
- Parent Signal.

### 3.3 Execution comment timeline

When an Action Plan execution is linked to a Signal, the execution comment section displays one combined timeline:

- inherited comments from the linked Signal,
- comments created directly on the execution.

Each comment item must expose its origin:
- `signal`
- `action_plan_execution`

The UI may display this origin as a small badge or contextual label.

Sorting rule:

```txt
oldest comment at the top
newest comment at the bottom
```

If two comments have the same creation time, ordering must remain deterministic.

## 4. Mentions

Users can mention other users with `@`.

Mention rule V1:

```
Any active member of an establishment can mention any active member of the same establishment.
```

There is no filtering by:

- role,
- Business Unit scope,
- Manager/Staff scope,
- Signal visibility,
- Action Plan execution visibility.

Mention validation is server-side.

A mentioned user must:

- have an active membership in the same establishment,
- be linked to an active user account.

Invalid mentions must be rejected.

Examples of invalid mentions:

- membership from another establishment,
- deactivated membership,
- invited but not active membership,
- inactive user account,
- unknown membership id.

Mentions on **execution comments** grant **participation in the thread** for the mentioned member:

- read execution detail (`action_plan_execution_readable_to_membership`),
- read execution comment list,
- reply to execution comment threads,
- appear in Action Plan Execution Feed **Ma vue** (`view_mode=personal`).

This does **not** grant operational rights on the execution (validate, cancel, mark_done, reassign, edit) nor manager/staff actionability beyond the existing RBAC rules (`action_plan_execution_visible_to_membership`).

Mentions on **Signal comments** do not grant Action Plan execution access, including inherited Signal comments shown on execution detail.

Mention notifications are implemented (`comment.mention.created`); payloads remain non-sensitive (no comment body).

## 5. Permissions

Comments follow the visibility of their parent business object.

### 5.1 Signal comments

A user can list Signal comments if they can view the Signal detail.

A user can create a Signal comment if they can view the Signal detail.

Signal comment permissions must be enforced by the backend.

Frontend permission checks are UX only.

### 5.2 Action Plan execution comments

A user can list execution comments if they can view the Action Plan execution detail (including mention-granted read access).

A user can create an execution comment if they can view the Action Plan execution detail.

Execution comment permissions must be enforced by the backend.

Frontend permission checks are UX only.

## 6. Content rules

A comment body is plain text.

V1 does not support rich text, markdown rendering, file attachments, or embedded media.

Recommended constraints:

- body is required,
- body is trimmed server-side,
- empty body is rejected,
- max length: 2,000 characters.

The comment body is user-generated operational content and must be treated as sensitive.

Comment content must not be logged, sent to AI, exposed in technical events, or stored in frontend persistent storage.

## 7. HTTP

[`apps/api/schema.yml`](../../../apps/api/schema.yml). Signal and action-plan-execution comment list/create; execution comments also have resolve/unresolve. POST body: `body`, `mentioned_membership_ids`. Comment body is sensitive — never in logs, AI, generic realtime, or durable frontend storage.

## 8. Frontend

List items carry `origin`: `signal` for Signal comments (including inherited rows on execution detail); `action_plan_execution` for direct execution comments. UI: Signal detail and Action Plan execution detail; mobile-first; empty/error/unauthorized explicit. Composer: required trimmed body, max 2,000 characters; disable submit while pending.

## 9. Non-goals V1

The following are explicitly out of scope:

- comment edit/delete,
- attachments,
- reactions,
- moderation workflow,
- audit export,
- advanced pagination unless needed by implementation constraints,
- chat integration,
- AI analysis.

**Operational realtime (in scope):** comment list refresh via establishment-scoped WebSocket **invalidation**. Backend emits `comment.*` from `comments/services.py` after sync writes; frontend refetches authorized queries — no comment body on the socket. [`realtime_domain.md`](realtime_domain.md).
