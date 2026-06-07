# Feed Subscription Domain

Status: authoritative (contract)  
Last reviewed: 2026-05-29  
Implementation status: **deferred** — doc Phase A only (V5). **Out of scope for Phase 4 MVP**; Ma vue uses `MembershipScope` instead.

> **Deferred / v1 obsolete:** When implemented, subscriptions will target **BusinessUnit** (not Module/Domain/Subject). See [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md).

## Purpose

Feed subscriptions personalize **Ma vue** (`view_mode=personal`). They are **not** security permissions.

## Scope

- User may subscribe at **BusinessUnit** level (future).
- Unit subscriptions are **out of scope** for MVP.
- Subscriptions do not grant action rights; RBAC remains on BusinessUnit `MembershipScope` and role rules.

## Main object (future)

`MembershipFeedSubscription`

| Field | Description |
| --- | --- |
| `membership` | FK EstablishmentMembership |
| `kind` | `module` \| `domain` \| `subject` |
| `operational_module` | FK when kind=module |
| `operational_domain` | FK when kind=domain |
| `operational_subject` | FK when kind=subject |
| `active` | bool |

Exactly one target FK set per row, enforced by check constraint.

## Matching rule

A Signal matches a subscription when **any** level matches:

- Module subscription → all Signals with same `operational_module`
- Domain subscription → all Signals with same `operational_domain`
- Subject subscription → Signals with same `operational_subject` only

## View modes

| Mode | API | Content |
| --- | --- | --- |
| Ma vue | `view_mode=personal` | Active Signals matching user's feed subscriptions |
| Vue générale | `view_mode=general` | All active establishment Signals (RBAC only, no subscription filter) |

## Separation from RBAC

| Concern | Owner |
| --- | --- |
| Action on Signal | RBAC (`MembershipScope`) + role rules |
| Ma vue content | `MembershipFeedSubscription` |
| Feed access (can open feed) | `can_view_signal_feed` + establishment membership |

## Implementation gate (V5)

**Do not** create model, migration, or API until Signal model and Signal Feed selectors exist (Phase 4 E+F).

Candidate endpoints (future):

- `GET/PUT /api/v1/memberships/{id}/feed-subscriptions/`

## Future test scenarios (Phase 4 — documentation only)

Do **not** implement model, migration, service, API, or tests before Signal + Signal Feed selectors exist (gate V5).

### Model / service

| Scenario | Expected behavior |
| --- | --- |
| Create module subscription | Exactly one FK set: `operational_module` non-null; domain/subject null |
| Create domain subscription | `operational_domain` non-null; module/subject null |
| Create subject subscription | `operational_subject` non-null; module/domain null |
| Target FK from another establishment | Validation error |
| Replace subscriptions (PUT) | Deletes previous rows; creates new set atomically |
| Duplicate `(kind, key)` in same PUT | Deduped to one row |
| Unknown runtime key | 400 with stable error message |

### API authorization

| Scenario | Expected behavior |
| --- | --- |
| Member GET/PUT own membership subscriptions | 200 |
| Member GET/PUT another user's membership | 403 |
| Unknown membership or establishment | 404 |

### Matching integration (with Signal Feed)

| Subscription | Signals returned in Ma vue |
| --- | --- |
| Module-level | All Signals sharing that module |
| Domain-level | All Signals sharing that domain |
| Subject-level | Signals sharing that subject only |

Implement `MembershipFeedSubscription` **together with** Signal model and feed selectors — never as an orphan model or API.
