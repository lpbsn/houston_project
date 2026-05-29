# Action Domain

Status: authoritative
Last reviewed: 2026-05-29
Implementation status: not_started

## 1. Purpose

This domain defines Houston's concrete operational execution work linked to Signals.

Action owns:
- the executable work item created from a parent Signal in MVP
- assignment to one responsible assignee per Action
- the Action lifecycle from creation through execution, validation, cancelation, or reopen

Action does not own:
- raw Observation input or Observation privacy policy
- Signal lifecycle rules beyond Action-side dependencies
- feed sorting, pagination, or query composition
- notification routing rules, comment internals, realtime transport, or RBAC internals

Action is the execution object in the loop between Signal and validated operational completion. It is not the Signal itself, the raw Observation, or a checklist task.

## 2. MVP Scope

- Action creation from a parent Signal by an authorized user.
- One assignee per Action.
- Backend-owned lifecycle statuses for execution and validation.
- Assignee execution flow from assigned work to pending validation.
- Manager or otherwise authorized validation flow to final completion.
- Cancel and reopen boundaries as Action lifecycle concepts.
- Validated parent Signal side effects from Action lifecycle changes.
- Safe Action context linked to the parent Signal without exposing raw Observation text.
- Action relationship to Execution Feed, comments, notifications, realtime invalidation, and RBAC as domain boundaries.

## 3. Out of Scope

- Free-floating Actions not linked to a Signal.
- AI-created Actions.
- Direct Observation-to-Action creation.
- Treating Action as a Signal, Observation, ticket, or ChecklistTask.
- Multi-assignee single Action.
- Frontend-only lifecycle transitions or Signal side effects.
- Proof or photo evidence workflows not separately validated.
- Independent Action priority, SLA, recurring Actions, bulk Actions, public links, or arbitrary workflow customization.

## 4. Core Invariants

- Action is concrete execution work linked to exactly one parent Signal in MVP.
- Action is not Signal, Observation, or ChecklistTask.
- No free-floating Actions in MVP.
- AI does not create Actions in MVP.
- Backend services own Action lifecycle transitions and authorization.
- Frontend local state is never the authority for Action status.
- Assignee accept is the MVP start action and moves the Action to `in_progress`.
- `reopened` behaves like an open/open-like execution state and requires assignee acceptance before execution resumes.
- Parent Signal side effects are backend-owned: first Action creation moves the Signal to `in_progress`; when all linked Actions are `done` or `canceled`, the Signal moves to `resolved`.
- Creator and assignee are distinct concepts; whether the same user may fill both roles is a separate permission rule.
- One Action has one assignee; multiple assignees require multiple Actions.
- A parent Signal can become resolved when all linked Actions are terminal: `done` or `canceled`.
- Visibility does not imply command authority.
- Action must not expose raw Observation text in detail views, feeds, notifications, realtime payloads, or normal technical logs.
- Realtime and notifications may refresh attention, but they do not grant access and do not carry business truth.
- **Action inherits operational taxonomy from its parent Signal** — `operational_module`, `operational_domain`, `operational_subject`, and optional `operational_unit` are copied or derived from the parent Signal at creation. Actions do **not** define an independent taxonomy layer in MVP.
- Action domain keys used for RBAC (`MembershipDomain`) and Execution Feed filtering refer to the **inherited** Signal domain, not a separate Action taxonomy.

## 5. Main Objects

- `Action`
  - Concrete execution work created from one parent Signal.
  - Assigned to one active establishment member in MVP.
  - Inherits parent Signal operational taxonomy (module, domain, subject, optional unit).

- `ActionTaxonomyContext`
  - Read-only projection of parent Signal categorization for RBAC and Execution Feed.
  - Not a separate editable taxonomy on the Action row in MVP.

- `ActionStatus`
  - Lifecycle state such as `open`, `in_progress`, `pending_validation`, `done`, `canceled`, or `reopened`.
  - `reopened` is an execution restart state that behaves like open/open-like work waiting for assignee acceptance.

- `ActionAssignee`
  - The active member responsible for execution.
  - Distinct from the creator.

- `ActionCreator`
  - The authorized user who creates the Action from the Signal.
  - Creation authority depends on RBAC and parent Signal access.

- `ActionValidation`
  - Authorized confirmation that execution is complete.
  - Separate from assignee execution.

- `ActionCancellation`
  - Authorized closure without normal completion.
  - Exact reason and category requirements are not validated in current code.

- `ActionReopen`
  - Authorized return from validation to an open-like execution state.
  - Requires assignee acceptance before execution resumes.
  - Exact reason requirement is not fully defined yet.

- `ActionContext`
  - Safe parent Signal summary and related context for execution.
  - Must not include raw Observation text.

## 6. Lifecycle / Statuses

Target MVP lifecycle:
- `open`
  - Action created and assigned.
- `in_progress`
  - Action actively being executed.
- `pending_validation`
  - Assignee indicates the work is complete and awaits validation.
- `done`
  - Authorized validation completed.
- `canceled`
  - Action closed without normal completion.
- `reopened`
  - Action returned from validation back to execution.

Target MVP transitions:
- create from Signal -> `open`
- assignee accepts -> `in_progress`
- assignee marks done -> `pending_validation`
- authorized validator validates -> `done`
- authorized validator reopens -> `reopened`; `reopened` behaves like an open/open-like execution state
- `reopened` -> assignee accepts -> `in_progress`
- `in_progress` -> assignee marks done -> `pending_validation`
- authorized user cancels -> `canceled`

Accept is the implicit start command in MVP; there is no separate start command unless later validated.

Not validated yet:
- exact cancel and reopen reason requirements or category lists

## 7. Permissions

- Action visibility is establishment-scoped and backend-authorized.
- Action creation requires authorized access to the parent Signal plus backend command authorization.
- Current code truth in `apps/api/houston/establishments/permissions.py` validates that `owner`, `director`, and `manager` can create and validate Actions, while `staff` cannot.
- Current code truth does not yet validate Action-specific object-level rules such as assignee execution, reassignment, cancel, reopen, or domain-matching checks on concrete Action resources.
- Product direction expects assignee execution and manager validation to remain separate responsibilities.
- Notifications and realtime events do not grant Action access.
- Exact role-by-command and domain-by-command Action rules remain candidate until Action services and APIs exist.

## 8. Events

No implemented Action event contract is validated in current code or in `apps/api/schema.yml`.

Candidate events only:
- `ActionCreated`
- `ActionAssigned`
- `ActionAccepted`
- `ActionMarkedDone`
- `ActionPendingValidation`
- `ActionValidated`
- `ActionReopened`
- `ActionCanceled`

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented Action endpoints confirmed in `apps/api/schema.yml`:
- none

Candidate endpoints only:
- create Action from Signal
- fetch Action detail
- accept Action
- mark Action done
- validate Action
- reopen Action
- cancel Action
- reassign Action

Do not treat any Action endpoint as implemented until it exists in `apps/api/schema.yml`.

## 10. Frontend Expectations

- When implemented, Execution Feed may show backend-authorized Actions as execution work items.
- **Execution Feed Ma vue (`view_mode=personal`)** filters by **assigned operational responsibilities** (assignee, creator where product allows, checklist assignment) — **not** by `MembershipFeedSubscription`.
- Signal Feed Ma vue uses feed subscriptions; Execution Feed Ma vue uses assignment/responsibility rules. See [`feed_domain.md`](feed_domain.md).
- Action cards and detail views must show safe Action context, not raw Observation text.
- Frontend may render backend-provided permission hints, but backend responses remain the authority for all commands.
- Lifecycle changes must be sent as backend commands, not applied as frontend-owned state transitions.
- Frontend must not infer parent Signal status changes locally after Action commands.
- Realtime remains invalidation and refetch only; it does not carry business truth.
- Notifications and realtime payloads must not be treated as complete Action state.
- TanStack Query owns server state for implemented Action APIs.
- Frontend must use generated OpenAPI clients only for routes present in `apps/api/schema.yml`.

## 11. AI Agent Notes

- Inspect current Action code before claiming models, services, statuses, commands, events, or endpoints exist.
- Inspect `apps/api/schema.yml` before listing any Action API as implemented.
- Inspect `signal_domain.md` before changing Action creation from Signal or Signal-side effects.
- Inspect `rbac_permissions_domain.md` before changing Action visibility or command authorization.
- Inspect `observation_domain.md` and `security_rgpd_domain.md` before changing raw-text visibility or logging boundaries.
- Inspect [`feed_domain.md`](feed_domain.md) before changing Execution Feed personal vs general assumptions.
- Do not add independent Action module/domain/subject fields unrelated to the parent Signal in MVP.
- Do not add a separate start command unless explicitly validated; assignee accept is the MVP start behavior.
- Do not make Action a Signal, Observation, ChecklistTask, generic ticket, or free-floating task.
- Do not let AI create Actions in MVP.
- Do not expose raw Observation text in Action detail, feed, notifications, realtime payloads, or normal technical logs.
- Do not implement frontend-only Action lifecycle transitions.
- Do not leave parent Signal side effects to frontend inference; Signal transition side effects must be handled backend-side.
- When Action APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
