# Feed Subscription Domain

Status: authoritative (future contract)
Last reviewed: 2026-09-21
Implementation status: **deferred** — not implemented. **Today:** Signal Feed Ma vue uses `MembershipScope` (BusinessUnit) only.

Do not implement `MembershipFeedSubscription` until explicitly opened.

## Purpose

Future feed subscriptions will personalize **Ma vue** (`view_mode=personal`) for Signal Feed. They are **not** security permissions.

## Current behavior

| Concern | Owner |
| --- | --- |
| Signal Feed Ma vue content | `MembershipScope` (BusinessUnit match on affected/responsible) |
| Action on Signal | RBAC (`MembershipScope`) + role rules |
| Feed access (can open feed) | `can_view_signal_feed` + establishment membership |

## Target (deferred)

1. **BU-only subscriptions:** user subscribes/unsubscribes at BusinessUnit level; Ma vue shows Signals where affected or responsible BU matches a subscribed BU.
2. **ActivitySubject subscriptions:** finer Ma vue filtering under subscribed BusinessUnits.

General view (`view_mode=general`) remains all feed-visible establishment Signals (RBAC only). `OperationalUnit` subscriptions remain out of scope.

Subscriptions must not grant action rights or replace RBAC checks. HTTP, when opened, belongs in `schema.yml`.
