# Need scope

Frame the raw need before implementation.

Read-only mode:
- read `AGENTS.md`, relevant nested `AGENTS.md`, and `.cursor/rules/**`
- inspect existing docs/code/tests before concluding
- do not edit files
- do not create an implementation plan unless explicitly asked

Goal:
Turn the raw request into a precise, minimal, scalable implementation scope.

Analyze:
- real user/business objective
- affected Houston loop: Observation -> Signal -> Action -> Execution -> Validation -> Feed
- current behavior vs expected behavior
- backend source of truth: models, services, selectors, permissions, serializers/views
- frontend surfaces: routes, hooks, query keys, components, mobile/PWA states
- RBAC, membership, establishment isolation, owner/director/manager/staff rules
- API contract, OpenAPI/generated types, schema drift risk
- event-driven side effects, realtime invalidation, cache impact
- migrations/data backfill risk
- tests already present and missing coverage

Guardrails:
- backend owns business rules, permissions, lifecycle, visibility, validation
- keep writes in services
- keep reusable reads/feeds in selectors
- keep views thin
- keep React as UI only
- use generated API types and existing API wrappers
- use TanStack Query for server state
- preserve mobile-first UX and explicit loading/empty/error/unauthorized/offline states
- no unrelated refactor
- no dependency/version upgrade
- no manual edit of generated files
- no sensitive business payload in logs, events, WS payloads, or persistent frontend storage

Output:

## 1. Besoin reformulé
One clear paragraph.

## 2. Objectif réel
What must be true for the user/business after the change.

## 3. Scope minimal
- Backend:
- Frontend:
- API/types:
- Realtime/cache:
- Data/migration:
- Docs:

## 4. Hors scope
Explicitly list what should not be touched.

## 5. Risques / angles morts
Prioritize bugs, security, RBAC, tenant isolation, lifecycle, cache, mobile/PWA, scalability.

## 6. Options
Compare 2-3 implementation options only if there is a real trade-off.

For each option:
- approach
- pros
- cons
- risk level

## 7. Recommandation
Pick one option and explain why it is the safest/minimal/scalable choice.

## 8. Definition of Done
- expected behavior
- backend tests
- frontend tests
- negative tests
- validation commands
- docs/schema/types updated or explicitly not needed

## 9. Questions bloquantes
Only ask questions that block correct scoping.
If not blocking, make a reasonable assumption and state it.