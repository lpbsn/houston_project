## Socle commun — Audit Houston

Mode audit only.

Do not edit source code.
Do not modify app behavior.
You may create or update Markdown audit reports only under:
docs/audits/

Never edit source files during audit mode.
Context:
Houston is in dev phase only. No staging/prod compatibility requirement. No defensive migration strategy unless it protects data integrity or architecture.

Audit objective:
This is a technical/product codebase audit focused on:
- scalability
- code structure
- maintainability
- simplification
- optimization where it has real impact
- ambiguity detection
- bad practices
- duplicated patterns
- fragile architecture
- weak boundaries between domains
- backend/frontend responsibility drift
- missing tests around risky behavior

Read first:
- AGENTS.md
- nearest AGENTS.md for the audited area
- relevant .cursor/rules
- relevant docs when useful
- related code
- related tests

Audit mindset:
- Challenge the current implementation.
- Identify what will become painful as Houston grows.
- Find code that is hard to evolve, hard to test, ambiguous, duplicated, over-coupled, or misplaced.
- Prefer concrete repo evidence over generic best practices.
- Do not report theoretical issues without code evidence.
- Do not force a scalability angle when the issue is mainly structure, security, UX, testing, or clarity.
- If the code is already good enough, say so.

Look specifically for:
- unclear ownership between modules/domains
- business logic in the wrong layer
- duplicated permission or lifecycle logic
- frontend/backend contract drift
- weak API validation
- broad or expensive queries
- N+1 risks
- missing indexes or constraints
- over-broad cache invalidation
- fragile realtime/event behavior
- inconsistent UI/state handling
- oversized components/services/hooks
- unclear naming
- dead code
- stale docs
- missing regression tests
- tests that validate implementation details instead of behavior

Output rules:
Start with:
1. Files inspected
2. Tests inspected
3. Docs/rules inspected
4. Assumptions or unknowns

Then output max 10 findings.

For each finding:
- ID
- Severity: P0/P1/P2/P3
- Category: scalability / structure / maintainability / performance / security / API contract / tests / ambiguity
- Evidence: file + function/component/test reference
- Problem
- Why it matters now
- Why it will hurt later
- Recommended fix
- Tests to add/update
- Suggested implementation size: S/M/L

End with:
1. Top 3 fixes to do first
2. Quick wins
3. Structural issues to plan later
4. Things not worth fixing now