```
# Comments Domain — Signal & Action Comments

Status: Draft validated for implementation  
Scope: MVP / V1  
Related backlog:
- HOU-BACKLOG-005 — Ajouter les commentaires sur les Signaux
- HOU-BACKLOG-006 — Ajouter les commentaires sur les Actions

## 1. Purpose

Houston comments allow field and operational teams to add contextual written notes directly inside a Signal or an Action.

A comment is not a chat message.  
A comment belongs to a business object context:
- Signal
- Action

Comments are used to clarify, document, or coordinate around an operational item without changing its lifecycle, classification, assignment, or validation state.

## 2. Product scope V1

V1 supports:

- List comments on a Signal.
- Add a comment on a Signal.
- List comments on an Action.
- Add a comment on an Action.
- Display comment author.
- Display comment creation date/time.
- Display comments from oldest at the top to newest at the bottom.
- Mention active users of the same establishment with `@`.
- Display inherited Signal comments inside linked Actions.

V1 does not support:

- Chat behavior.
- Realtime updates.
- Notifications.
- Mention notifications.
- Push notifications.
- Unread counters.
- Comment edit.
- Comment delete.
- Comment reactions.
- Comment attachments.
- Comment moderation.
- Offline mutation queue.
- AI processing of comments.

## 3. Core product rules

### 3.1 Signal comments

A Signal comment is created from the Signal detail page.

A Signal comment is stored once.

If the Signal has linked Actions, the Signal comment is visible inside every linked Action.

Signal comments are inherited by linked Actions for visibility only. They must not be physically duplicated into each Action.

A Signal comment never changes:
- Signal classification.
- Signal status.
- Signal urgency.
- Signal responsible Business Unit.
- Signal affected Business Unit.
- Linked Actions.

### 3.2 Action comments

An Action comment is created from the Action detail page.

An Action comment belongs only to that Action.

An Action comment is not visible on the parent Signal.

An Action comment is not visible on other Actions linked to the same Signal.

An Action comment never changes:
- Action status.
- Action assignment.
- Action due date.
- Action validation state.
- Action classification.
- Parent Signal.

### 3.3 Action comment timeline

When an Action is linked to a Signal, the Action comment section displays one combined timeline:

- inherited comments from the linked Signal,
- comments created directly on the Action.

Each comment item must expose its origin:
- `signal`
- `action`

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
- Action visibility.

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

Mentions in V1 do not trigger notifications.

## 5. Permissions

Comments follow the visibility of their parent business object.

### 5.1 Signal comments

A user can list Signal comments if they can view the Signal detail.

A user can create a Signal comment if they can view the Signal detail.

Signal comment permissions must be enforced by the backend.

Frontend permission checks are UX only.

### 5.2 Action comments

A user can list Action comments if they can view the Action detail.

A user can create an Action comment if they can view the Action detail.

Action comment permissions must be enforced by the backend.

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

## 7. API behavior

Expected endpoints:

```
GET  /api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/
POST /api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/

GET  /api/v1/establishments/{establishment_id}/actions/{action_id}/comments/
POST /api/v1/establishments/{establishment_id}/actions/{action_id}/comments/
```

POST request:

```
{
  "body": "Peux-tu regarder ce point ?",
  "mentioned_membership_ids": ["uuid"]
}
```

Comment response item:

```
{
  "id": "uuid",
  "origin": "signal",
  "body": "Peux-tu regarder ce point ?",
  "author": {
    "membership_id": "uuid",
    "display_name": "Alice Martin"
  },
  "mentions": [
    {
      "membership_id": "uuid",
      "display_name": "Karim Dupont"
    }
  ],
  "created_at": "2026-06-15T10:30:00Z"
}
```

For Signal comments, `origin` is always `signal`.

For Action comments:

- inherited Signal comments return `origin = signal`,
- direct Action comments return `origin = action`.

## 8. UX contract

The comments section appears in:

- Signal detail page,
- Action detail page.

Default empty state:

```
Aucun commentaire pour l’instant.
```

Composer placeholder:

```
Ajouter un commentaire...
```

Submit behavior:

- submit button is disabled while pending,
- empty body cannot be submitted,
- failed submission displays an explicit error,
- successful submission refreshes the comment list.

The UI must be mobile-first:

- comfortable tap targets,
- no hover-only interaction,
- no horizontal scroll,
- composer usable on phone keyboard,
- loading, empty, error, and unauthorized states explicit.

## 9. Non-goals V1

The following are explicitly out of scope:

- notifications,
- mention notifications,
- realtime invalidation,
- WebSocket updates,
- unread state,
- chat integration,
- AI analysis,
- edit/delete,
- attachments,
- reactions,
- moderation workflow,
- audit export,
- advanced pagination unless needed by implementation constraints.

## 10. Acceptance criteria

### Signal comments

- A user who can view a Signal detail can list its comments.
- A user who can view a Signal detail can create a comment.
- A user who cannot view the Signal cannot access its comments.
- Signal comments are visible inside linked Actions.
- Signal comments are stored once and not duplicated per Action.
- Signal comments do not modify Signal classification or lifecycle.
- Mentions are limited to active memberships of the same establishment.
- Invalid mentions are rejected.
- No notification, realtime, or chat behavior is introduced.

### Action comments

- A user who can view an Action detail can list its comments.
- A user who can view an Action detail can create a comment.
- A user who cannot view the Action cannot access its comments.
- Action comments remain linked only to the Action.
- Action comments are not visible on the parent Signal.
- Action detail displays inherited Signal comments and direct Action comments in one chronological timeline.
- Action comments do not modify Action lifecycle or assignment.
- Mentions are limited to active memberships of the same establishment.
- Invalid mentions are rejected.
- No notification, realtime, or chat behavior is introduced.

## 11. Implementation guidance

Implementation must follow Houston conventions:

- Backend owns permissions, validation, visibility, and business rules.
- Frontend uses backend API contracts and generated types.
- Frontend must not duplicate authorization logic.
- TanStack Query owns frontend server state.
- No direct fetch calls from React components.
- No manual edits to generated API files.
- No sensitive comment body in logs, events, broker messages, WebSocket payloads, or persistent frontend storage.

Recommended backend structure:

```
houston.comments
  models.py
  permissions.py
  selectors.py
  services.py
  api/serializers.py
  api/views.py
  api/urls.py
  tests/
```

Recommended frontend structure:

```
apps/web/src/features/comments/
  api.ts
  hooks.ts
  types.ts
  components/comment-section.tsx
  components/comment-composer.tsx
  components/comment-list.tsx
```

These structures are recommendations. The implementation may adapt them if the repository already contains a stronger convention.