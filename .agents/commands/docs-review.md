# Docs review

Review living documentation directly affected by **the current change**.

**Scope:** same as other review Commands — user intent first, else Git (working tree → staged → branch vs base → last commit only when clearly intended). Do not touch unrelated user changes.

Update living docs when the change makes them false, incomplete, or misleading.

Do not document implementation noise. Do not rewrite historical or archive material merely to reflect the present. Prefer replacing stale content, removing obsolete instructions, simplifying, or deleting misleading history. Git is the history.

Distinguish living/authoritative docs, temporary design/roadmap docs, and archived docs.

Stop when living docs affected by this change are true again.
