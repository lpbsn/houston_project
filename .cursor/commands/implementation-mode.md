# Implementation Mode

Use this when implementing a feature, fix, or refactor.

Before editing:

* Read the relevant guardrails:

  * `AGENTS.md`
  * `apps/api/AGENTS.md` if backend/API is involved
  * `apps/web/AGENTS.md` if frontend/PWA is involved
  * relevant `.cursor/rules/*`
* Inspect existing code, tests, API contracts, docs, and conventions.
* Propose a short plan before coding.

Implementation rules:

* Houston is in dev phase only. No staging/prod compatibility requirement. No defensive migration strategy unless it protects data integrity or architecture
* Backend is the source of truth for business-critical logic.
* Frontend consumes backend state, permissions, hints, and capabilities; do not duplicate authoritative RBAC or domain rules.
* Preserve security, RBAC, establishment scoping, transactions, and data integrity.
* Build for scalability: avoid duplicated logic, N+1 queries, broad cache invalidations, unscoped selectors, hidden coupling, and fragile shortcuts.
* Keep the product goal in mind: Houston is a mobile-first PWA/web app built for operational teams in real-world environments.
* UI must stay mobile-first, fast, resilient, accessible, and usable under operational constraints.
* Follow existing event-driven, realtime, async, and cache patterns.
* Prefer small coherent changes over broad refactors.
* If API contracts change, update backend, generated frontend types/usages, and tests.
* Check active documentation and update it when behavior, contracts, permissions, realtime, setup, or workflow changes.

Validation :
* tests ciblés
* checks utiles selon fichiers touchés
* git status

Workflow:

1. Analyze impacted backend/frontend/API/realtime/cache/tests/docs.
2. Implement the smallest coherent change.
3. Add or update focused tests.
4. Run relevant targeted checks.
5. Report:

   * files changed
   * behavior changed
   * docs updated or why not needed
   * tests/checks run
   * Still open
   * Risks
   * risks / not verified
