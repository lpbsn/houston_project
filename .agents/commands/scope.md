# Scope

Frame the request before implementation. **Read-only** — do not edit files unless explicitly asked.

Read `AGENTS.md`, relevant nested `AGENTS.md`, and related code/tests first.

Analyze: user objective, Houston loop impact, current vs expected behavior, backend (models/services/permissions/API), frontend (routes/hooks/queries/Web vs Native states), RBAC/tenant isolation, API/schema drift, event/realtime/cache, migrations, existing vs missing tests.

Output:

## Reformulated need
One clear paragraph.

## Real objective
What must be true after the change.

## Minimal scope
Backend · Frontend · Native/runtime · API/types · Realtime/cache · Data/migration · Docs

## Out of scope
What must not be touched.

## Risks / blind spots
RBAC, lifecycle, cache, Web vs Native (Capacitor) loading/error/offline without SW, scalability.

## Recommendation
Safest minimal approach (2–3 options only if real trade-off).

## Definition of done
Behavior, tests (backend/frontend/negative), validation commands, docs/schema/types updated or explicitly not needed.

## Blocking questions
Only if they block correct scoping; otherwise state assumptions.
