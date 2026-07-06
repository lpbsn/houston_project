# Diff review

Review the latest diff before commit.

Use the repo context:
- `AGENTS.md`
- relevant nested `AGENTS.md`
- relevant `.cursor/rules/**`

Stay read-only unless I explicitly ask for fixes.

Inspect the latest meaningful diff:
- staged diff first
- otherwise working tree diff
- otherwise branch diff against `main`
- otherwise last commit

Review for:
- bugs, regressions, edge cases
- security, RBAC, tenant isolation, sensitive data leaks
- backend/frontend convention drift
- API contract, schema, generated types, query invalidation drift
- mobile-first / PWA regressions
- missing or weak tests
- stale docs caused by this diff

Do not be exhaustive for the sake of being exhaustive.
Focus on real risks introduced by the diff.

Output:

## Blockers
Must fix before commit.

## Risks
Important issues or weak points.

## Docs / tests
Only what is directly impacted.

## Validation
Smallest useful commands.

## Verdict
OK to commit / OK after fixes / Not safe.