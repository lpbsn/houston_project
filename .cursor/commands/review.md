# Review

Review the latest diff before commit. **Read-only** unless explicitly asked to fix.

Context: `AGENTS.md`, relevant nested `AGENTS.md`, relevant `.cursor/rules/**`.

Inspect diff priority: staged → working tree → branch vs `main` → last commit.

Checklist:
- API contract, schema, generated types, query invalidation drift
- RBAC, tenant isolation, sensitive data leaks
- lifecycle consistency, migrations
- mobile/PWA loading/error/offline states
- weak or missing tests; unnecessary refactor or duplication

Focus on risks **introduced by this diff** — not exhaustive noise.

Output:

## Blockers
Must fix before commit.

## Risks
Important issues or weak points.

## Docs / tests
Only what this diff impacts.

## Validation
Smallest useful commands (prefer `ARGS=` for backend tests).

## Verdict
OK to commit / OK after fixes / Not safe.
