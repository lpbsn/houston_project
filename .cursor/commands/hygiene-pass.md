# Hygiene pass

Clean only code made obsolete or noisy by **the current change**.

**Scope:** same as other review Commands — user intent first, else Git (working tree → staged → branch vs base → last commit only when clearly intended). Do not touch unrelated user changes.

Allowed: unused imports introduced by the change; helpers the change made obsolete; transitional branches the change made unnecessary; duplication the change introduced; comments the change directly invalidated.

Out of scope: unrelated historical debt, nearby refactors, cleanup “while here”, stylistic rewrites.

Stop when noise from this change is gone.
