# Feed Subscription Domain

Status: authoritative (future contract)  
Last reviewed: 2026-06-08  
Implementation status: **deferred** — not implemented. **Today:** Signal Feed Ma vue uses `MembershipScope` (BusinessUnit) only.

> **Not active product truth.** Do not implement `MembershipFeedSubscription` v1 (Module/Domain/Subject). See [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md).

## Purpose

Future feed subscriptions will personalize **Ma vue** (`view_mode=personal`) for Signal Feed — tailoring which operational subjects a user sees. They are **not** security permissions.

## Current behavior (implemented)

| Concern | Owner |
| --- | --- |
| Signal Feed Ma vue content | `MembershipScope` (BusinessUnit match on affected/responsible) |
| Action on Signal | RBAC (`MembershipScope`) + role rules |
| Feed access (can open feed) | `can_view_signal_feed` + establishment membership |

## Target design (deferred — product direction)

Implementation order when opened in a future ticket:

1. **Phase A — BU-only subscriptions:** user subscribes/unsubscribes at BusinessUnit level; Ma vue shows Signals where affected or responsible BU matches a subscribed BU.
2. **Phase B — ActivitySubject subscriptions:** user subscribes/unsubscribes at ActivitySubject level under subscribed BusinessUnits; finer Ma vue filtering by subject.

General view (`view_mode=general`) remains all active establishment Signals (RBAC only).

Unit (`OperationalUnit`) subscriptions remain out of scope for MVP.

## Separation from RBAC

| Concern | Owner |
| --- | --- |
| Action on Signal | RBAC (`MembershipScope`) + role rules |
| Ma vue content (future) | Feed subscription preferences |
| Ma vue content (today) | `MembershipScope` |

Subscriptions must not grant action rights or replace RBAC checks.

## Implementation gate

**Do not** create model, migration, or API in this deferred scope until explicitly opened. Signal Feed selectors exist; subscription layer is a future additive feature.

Candidate endpoints (future only):

- `GET/PUT /api/v1/memberships/{id}/feed-subscriptions/`

---

## Historical v1 design (obsolete — do not implement)

The Phase A v1 contract used `MembershipFeedSubscription` with `kind: module | domain | subject` and FKs to `OperationalModule`, `OperationalDomain`, `OperationalSubject`. That model is **obsolete** and removed with taxonomy v2 (Lot 6). Retained here for migration archaeology only.
