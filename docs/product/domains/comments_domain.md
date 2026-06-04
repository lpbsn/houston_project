# Comments Domain

Status: authoritative
Last reviewed: 2026-05-27
Implementation status: not_started

## 1. Purpose

Comments owns contextual discussion attached to authorized business objects.

- MVP comment subjects are `Signal` and `Action` only.
- Comments owns subject-scoped discussion visibility, creation boundaries, and mention-target boundaries at the domain level.
- Comments does not own Signal lifecycle, Action lifecycle, access grants, Notification routing, Realtime transport, Feed projections, Chat behavior, or Observation raw text.

## 2. MVP Scope

- Signal comments.
- Action comments.
- Subject-scoped comment read/create behavior in authorized Signal or Action context.
- Comment visibility inherited from the parent subject.
- Mention boundary for Signal and Action comments.
- Signal comments may appear in linked Action context as contextual read-only information.
- Action comments remain scoped to their specific Action.
- Backend authorization and establishment scoping.

## 3. Out of Scope

- Comments on Checklist subjects in MVP.
- Chat content.
- Comments as workflow transitions or hidden operational commands.
- Access grants through comments or mentions.
- Comment editing, deletion, moderation, or reporting unless separately validated.
- Replies, threading, reactions, attachments, comment search, or rich text complexity.
- Public or cross-tenant comments.
- AI-generated comments or AI comment summarization.
- Complete comment bodies in notification or realtime payloads.

## 4. Core Invariants

- A comment is contextual discussion, not a workflow state transition.
- Comment visibility and creation are subject-scoped.
- Backend authorization is required for comment reads and writes.
- Comments never create access.
- Mentions never extend access or visibility in MVP (comments not implemented).
- **Future exception (documented, not implemented):** mention on a Signal may grant narrow read + linked-Action create via `SignalAccessGrant` — see [`signal_access_grant_domain.md`](signal_access_grant_domain.md). Does not expand domain scope.
- Signal comments and Action comments have different scopes.
- Signal comments may be visible in linked Action context as read-only context.
- Action comments do not automatically propagate to sibling Actions or the parent Signal.
- System-generated comment behavior must not expose Observation raw text.
- System-generated comment behavior must not inject raw Observation text. User-authored comment bodies remain user input and must follow normal content/privacy rules.
- Full comment body is fetched only through authorized Signal or Action detail/comment APIs.
- Notification payloads must not carry the complete comment body.
- Realtime only invalidates or refetches authorized comment context.
- Checklist subjects are outside MVP comment scope.
- Chat remains separate from Comments.

## 5. Main Objects

- `Comment`
  - Subject-scoped discussion entry on an authorized `Signal` or `Action`.
  - Represents contextual discussion, not business workflow state.

- `CommentSubject`
  - Parent business object such as `Signal` or `Action`.
  - Determines visibility and comment permission boundaries.

- `CommentAuthor`
  - Authenticated establishment member who created the comment.
  - Must act through normal backend authorization.

- `Mention`
  - Product target user reference inside a Signal or Action comment.
  - Exact parsing and API request shape remain candidate until implemented.
  - May trigger targeted attention behavior, but never grants access.

- `CommentContext`
  - Safe comment view rendered inside authorized Signal or Action detail.
  - May include parent Signal context in linked Action views when validated.

- `CommentEvent`
  - Candidate event emitted when a comment is added or mention handling occurs.
  - Event payloads must stay minimal and non-sensitive.

## 6. Lifecycle / Statuses

- MVP lifecycle: `created`

Comment editing and deletion are out of MVP unless separately validated.

Candidate mention flow:
- parsed or validated
- notification candidate generated

## 7. Permissions

- Comment access is establishment-scoped through the parent subject.
- Reading comments requires authorized access to the parent `Signal` or `Action`.
- Creating comments requires authorized comment permission on the parent `Signal` or `Action`.
- Mentions do not grant subject visibility.
- Opening a mention notification must re-fetch the parent subject through normal authorization.
- Signal comment visibility follows Signal visibility.
- Action comment visibility follows Action visibility.
- Signal comments may appear in linked Action context only for authorized viewers of that linked context.
- Action comments do not appear on sibling Actions or globally on the parent Signal by default.
- Exact role-by-role comment rules are not validated yet in current code or `apps/api/schema.yml`.

## 8. Events

No implemented Comments event contract is validated in current code or `apps/api/schema.yml`.

Candidate events only:
- `SignalCommentAdded`
- `ActionCommentAdded`
- `CommentMentionCreated`
- `CommentUpdated` candidate only if editing is later validated
- `CommentDeleted` candidate only if deletion is later validated

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Schema-confirmed routes today:
- none

Candidate routes only:
- list Signal comments
- create Signal comment
- list Action comments
- create Action comment
- include parent Signal comments as a contextual read-only section in Action detail
- update or delete comment only if later validated

Candidate legacy API planning also referenced explicit mention inputs such as `mentioned_user_ids`, but no request shape is implemented in current schema truth.

## 10. Frontend Expectations

- Comments render only inside authorized Signal or Action detail surfaces.
- Frontend must not treat comments as workflow commands.
- Frontend must not inject or surface Observation raw text through system comment behavior.
- Optional mentions should be supported only if backend/API support exists.
- Frontend must not assume mentions create access.
- Frontend must use generated OpenAPI clients only for routes present in `apps/api/schema.yml`.
- TanStack Query owns comment server state when comment APIs exist.
- Realtime should invalidate or refetch comment context only.
- Chat UI must not reuse Comments behavior unless separately validated.

## 11. AI Agent Notes

- Inspect current comments code before claiming models, services, events, or APIs exist.
- Inspect `apps/api/schema.yml` before listing any Comments API as implemented.
- Inspect `signal_domain.md` before changing Signal comment behavior.
- Inspect `action_domain.md` before changing Action comment behavior.
- Inspect `notification_domain.md` before changing mention or comment attention behavior.
- Inspect `rbac_permissions_domain.md` before changing comment visibility or creation rules.
- Inspect `security_rgpd_domain.md` before changing body, payload, logging, or retention assumptions.
- Inspect `feed_domain.md` before changing any feed-facing comment summary assumptions.
- Do not make comments or mentions create access.
- Do not turn comments into workflow state transitions.
- Do not add comments to Checklist MVP scope.
- Do not expose Observation raw text through comments, notifications, realtime payloads, or normal logs.
- Do not send complete comment bodies in notification payloads.
- Do not add editing, deletion, moderation, threading, reactions, attachments, or search unless separately validated.
- When comment APIs are implemented later, update backend authorization, OpenAPI, generated clients, tests, notification boundaries, realtime invalidation, and this document together.
- This active reference is synthesized from current code/schema truth and adjacent validated domain docs because no legacy `houston_comments_domain.md` source exists in the repository.
