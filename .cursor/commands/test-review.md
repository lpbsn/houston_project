# Test review

Review test quality for **the current change**. Procedure: [`docs/engineering/testing.md`](../../docs/engineering/testing.md).

**Scope:** same as other review Commands — user intent first, else Git (working tree → staged → branch vs base → last commit only when clearly intended). Do not touch unrelated user changes.

Start with: (1) risk, (2) ownership layer, (3) existing coverage.

Prefer strengthening existing useful tests, deleting weak or redundant tests, and adding missing coverage at the appropriate layer.

Do not optimize for number of tests, coverage percentage, or duplicated integration tests. Tests should prove product or technical risk, not implementation trivia.

Validation: targeted `make backend-test ARGS='…'` or `cd apps/web && npm test -- …`; broader gates only when justified.

Report: Deleted · Refactored · Added · Validated · Remaining test debt.
