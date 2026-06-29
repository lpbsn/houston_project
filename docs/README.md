# Houston Documentation Index

## Active Documentation Rules

- `docs/00_ai_documentation_policy.md` is mandatory reading for documentation work.
- `AGENTS.md` files remain the primary coding-agent behavior instructions.
- `apps/api/schema.yml` is the current API truth.
- Product docs describe business decisions and target scope, not necessarily implemented endpoints.
- Build docs describe phased implementation.
- Architecture docs describe technical rules.
- Archived docs are historical only and must not drive implementation.

## Proposed Structure

```txt
docs/
  00_ai_documentation_policy.md
  README.md
  architecture/
  engineering/
  evolution_action/
  product/
  product/Build_Plan/
  api/
  archive/
```

Engineering standards (e.g. [`engineering/api_pagination_standard.md`](engineering/api_pagination_standard.md)) live under `docs/engineering/`.

Refonte Plan d'action (Lot -1 signé) :

- [`evolution_action/besoin_evolution_action.md`](evolution_action/besoin_evolution_action.md) — expression de besoin
- [`evolution_action/decisions_plan_action.md`](evolution_action/decisions_plan_action.md) — decision log §26 (`authoritative`)

This index does not require creating a larger doc tree immediately. It defines how the active documentation set should be read.

## How To Read The Docs

1. Start with the nearest `AGENTS.md`.
2. Use `apps/api/schema.yml` for current API truth.
3. Use architecture docs for technical constraints.
4. Use product docs for business decisions and target scope.
5. Use archive only for historical context.
