# Review changes

Review and correct **this change**. Do not assume the last commit is the target.

**Scope:** user intent first; otherwise Git — working tree, then staged, then branch vs relevant base, then last commit only when context clearly indicates it. Same scope as other review Commands; this Command examines correctness and architecture. Do not revert, absorb, reformat, or modify unrelated existing changes.

Before correcting anything: inspect the whole relevant diff (added/removed/renamed files, migrations, tests, docs, generated consequences). Expand into surrounding code only as needed for ownership and blast radius.

Review for: correctness, regressions, architecture, API/contracts, RBAC/security/integrity, database/query behavior, cache, async/realtime, realistic scalability, frontend surface behavior, tests/docs when relevant.

Correct objective defects directly. Do not silently introduce new product or architectural decisions.

After corrections: inspect the final diff again and rerun appropriate validations.

Output:

## Blockers

## Risks

## Docs / tests

Only what this change impacts.

## Validation

## Verdict

OK to commit / OK after fixes / Not safe.
