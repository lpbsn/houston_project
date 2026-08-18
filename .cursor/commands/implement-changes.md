# Implement changes

If a validated plan exists in this conversation, treat its product and architectural decisions as constraints. Follow it unless the repository invalidates a technical assumption. Adapt technical details when needed. Do not silently reopen validated decisions.

A validated plan is not required for a clearly scoped trivial or local request.

Read `AGENTS.md`, relevant nested `AGENTS.md`, existing code, and tests before editing.

- Smallest change that fits the architecture
- Reuse existing patterns; no speculative abstractions, compatibility layers, or dual paths for hypothetical consumers
- Do not touch unrelated user changes
- Validate the changed behavior first, then the likely blast radius

If **external** API request/response semantics change, consider the end-to-end contract chain regardless of which file triggered the change. Do not hand-edit generated artifacts. Do not regenerate schema or frontend types when the external contract is unchanged. Scoped Rule `api-contract.mdc` is automatic context for high-probability contract files; it is not a complete detector.

Native keyboard / safe-area / Web vs Native runtime diagnosis: Skill `native-runtime-debug`.

Backend tests: `make backend-test ARGS='…'` (Docker). Never `cd apps/api && uv run` on the host.

Report: Changed · Validated · Risks / not verified.
