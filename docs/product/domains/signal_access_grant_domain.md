# Signal Access Grant Domain (candidate)

Status: candidate — not implemented in Phase 5  
Last reviewed: 2026-06-03  
Implementation status: not_started

## Purpose

Future narrow access to a **single Signal** without granting full operational-domain visibility.

## Planned behavior (comments phase)

- Created when a user is **mentioned** on a Signal comment.
- Grants: read Signal detail, create **linked** Actions on that Signal.
- Does **not** grant: Signal Feed domain visibility, unrelated Signals, or Action taxonomy bypass.

## Phase 5

No model, API, or tests. Action creation uses `MembershipScope` + active Signal rules only.
