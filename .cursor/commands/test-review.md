# Test review

Review test quality for **the current change**. Procedure: [`docs/engineering/testing.md`](../../docs/engineering/testing.md).

**Scope:** same as other review Commands — user intent first, else Git (working tree → staged → branch vs base → last commit only when clearly intended). Do not touch unrelated user changes.

Start with: (1) risk, (2) ownership layer, (3) existing coverage.

Before keeping or adding a backend test, check: **owning layer?** **already asserted in a matrix, corpus, or isolation table?** **extend vs new file?** Do not add `test_*lot*`, `*_spike*`, a versioned golden beside the current apply-side corpus, a new journey that only re-wires covered domains, or a per-endpoint isolation file. Cross-establishment cases belong in one parametrized table per domain.

Before keeping or adding a frontend test, check: **owning layer?** **copy/class justified as a contract?** **already asserted in lib/hook?**

Prefer strengthening existing useful tests, deleting weak or redundant tests, and adding missing coverage at the appropriate layer.

Do not optimize for number of tests, coverage percentage, or duplicated integration tests. Tests should prove product or technical risk, not implementation trivia.

Validation: targeted `make backend-test ARGS='…'` or `cd apps/web && npm test -- …`; broader gates only when justified.

Report: Deleted · Refactored · Added · Validated · Remaining test debt.
