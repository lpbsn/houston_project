# Phase 0.7 — Phase 0 Closure Gate

## Status

Planned.

## Context

Phase 0 is the technical and identity/access foundation of Houston.

Previous Phase 0 slices:

- Phase 0.1 — Foundations
- Phase 0.2 — Foundation Hardening
- Phase 0.3 — Core Technical Primitives
- Phase 0.4 — Identity & Access Foundation
- Phase 0.5 — Web Auth Foundation
- Phase 0.6 — Minimal RBAC / Permission Service Foundation

Phase 0.7 is not a feature phase.

It is a closure gate before Phase 1.

Its purpose is to prove that the project foundation is clean, tested, documented, and ready for Runtime Configuration + Minimal Onboarding.

## Mandatory Reading Before Planning

Before producing any plan or modifying files, Codex must inspect the existing repository.

Codex must not rely only on this phase document or assumptions.

Codex must read, at minimum:

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `Makefile`
- `apps/api/config/settings.py`
- `apps/api/config/urls.py`
- `apps/api/houston/accounts/models.py`
- `apps/api/houston/accounts/views.py`
- `apps/api/houston/accounts/forms.py`
- `apps/api/houston/organizations/models.py`
- `apps/api/houston/establishments/models.py`
- `apps/api/houston/establishments/access.py`
- `apps/api/houston/establishments/permissions.py`
- `apps/api/houston/core/views.py`
- `apps/api/houston/core/urls.py`
- existing tests under `apps/api/houston/`
- existing templates under `apps/api/houston/`

Codex must also read these Codex phase documents:

- `docs/codex/phase_0_1_foundations.md`
- `docs/codex/phase_0_2_foundation_hardening.md`
- `docs/codex/phase_0_3_core_primitives.md`
- `docs/codex/phase_0_4_identity_access_foundation.md`
- `docs/codex/phase_0_5_web_auth_foundation.md`
- `docs/codex/phase_0_6_minimal_rbac_permission_service.md`

Codex must also read these product / cadrage documents:

- `docs/product/houston_product_overview.md`
- `docs/product/houston_technical_architecture_erd_final.md`
- `docs/product/houston_authentication_identity_domain.md`
- `docs/product/houston_rbac_permissions_domain.md`
- `docs/product/houston_api_contract_mvp.md`
- `docs/product/houston_security_rgpd_baseline.md`
- `docs/product/Build_Plan/houston_mvp_build_plan.md`

If one of these files does not exist, Codex must explicitly say so in the plan.

The plan must include a section named:

`Repository And Phase 0 Facts Inspected`

This section must list:

- each repository file inspected
- each product / cadrage document inspected
- relevant product constraints found
- relevant technical constraints found
- current Phase 0 implementation status
- current migrations status
- current test structure
- current validation command status if known
- current README/docs gaps
- conflicts or ambiguities between phase docs, README, code, and product cadrage

If Codex does not include this section, the plan must be rejected.

## Business Goal

Close Phase 0 safely before starting Phase 1.

Phase 0 is considered closed only when Houston has:

- stable Django project foundation
- Docker-based development workflow
- PostgreSQL + Redis wiring
- pytest + Ruff + OpenAPI generation
- core technical primitives
- identity/access models
- web session authentication
- current establishment context
- minimal permission service
- validation commands passing
- documentation reflecting the real current state

## Technical Goal

Perform a full foundation audit and update only the minimal documentation or configuration required to make Phase 0 coherent.

This phase should mostly verify.

It may only modify documentation or small project metadata if stale.

It must not add business-domain code.

## `houston.core` Closure Gate

Phase 0 closure must preserve `houston.core` as a narrow technical layer, not a generic dumping ground.

Allowed in `houston.core` only:

- generic abstract base models
- cross-cutting technical primitives
- generic result objects
- generic exceptions
- generic event envelope structures
- temporary health, root, and app shell views
- helpers that are genuinely shared and non-business

Forbidden in `houston.core`:

- Observation business logic
- Signal business logic
- Action business logic
- Checklist business logic
- Notification business logic
- Upload business logic
- AI business logic
- establishment-specific RBAC rules
- domain services
- business selectors
- object-level business policies
- code added there only because it is reused by two files

Decision rule:

- if code depends on a business concept, it must live in the owning domain app
- if code is shared across domains but still carries business rules, it must live in the owning domain or a dedicated app, never in `core`
- if there is doubt, do not place the code in `houston.core`

PR review rule:

- any PR that adds code to `houston.core` must explicitly justify why the addition is framework-level or infrastructure-level rather than domain-level
- reviewers should reject convenience-driven additions that weaken domain boundaries

## In Scope

### Phase 0 audit

Audit that the following foundations exist and are coherent:

- project structure under `apps/api`
- Django settings
- installed apps
- URL routing
- health endpoint
- root page
- OpenAPI schema generation
- pytest configuration
- Ruff configuration
- Docker Compose workflow
- Makefile commands
- core primitives
- `User`
- `Organization`
- `Establishment`
- `EstablishmentMembership`
- web login/logout
- protected `/app/`
- current establishment access context
- minimal RBAC permission service
- migrations
- tests
- docs/codex phase files
- README status

### Documentation cleanup

Codex may update documentation only if it is stale or inaccurate.

Allowed documentation updates:

- `README.md`
- `docs/codex/phase_0_7_phase_0_closure_gate.md` if implementation notes are needed
- architecture guardrails documenting what may and may not live in `houston.core`

Recommended README updates:

- current completed phase status
- validation commands
- current app capabilities
- explicit “not yet implemented” section
- next phase: Phase 1 — Runtime Config + Minimal Onboarding

### Validation checklist

Codex must produce or update a clear validation checklist.

Required validation commands:

```bash
make check
make test
make lint
make schema

Required migration check:
cd apps/api
uv run python manage.py makemigrations --check --dry-run
Optional direct commands:
cd apps/api
uv run python manage.py check
uv run pytest
uv run ruff check .
uv run python manage.py spectacular --file schema.yml
Out-of-scope audit
Codex must verify that no premature business domains were introduced.
The repository must not contain implementation for:
Observation
Signal
Action
Checklist
Comments
Notifications
Realtime business flows
AI pipeline
Upload flows
Onboarding runtime config
invitation flow
JWT
refresh tokens
React
apps/web
Codex must also verify that `houston.core` has not become a host for domain services, business selectors, business policies, or establishment-specific RBAC logic.
Existing empty Django app folders from Phase 0.1 are acceptable if they were already part of the foundation.
Out of Scope
Do not implement:
Phase 1 onboarding
runtime configuration
operational modules
operational domains table
operational units
invitations
signup
password reset
JWT
refresh tokens
DRF login endpoint
Observation
Signal
Action
Checklist
Comments
Notifications
Realtime
Celery jobs
Channels consumers
AI pipeline
Upload logic
React
TypeScript
apps/web
Do not add new dependencies.
Do not create migrations unless a serious existing inconsistency is found and explicitly justified in the plan.
Do not refactor working Phase 0 code unless a concrete validation failure requires it.
Expected Files
Codex may modify:
README.md
docs/codex/phase_0_7_phase_0_closure_gate.md
Codex may inspect but should normally not modify:
apps/api/config/settings.py
apps/api/config/urls.py
apps/api/houston/**
migrations
tests
If Codex proposes code changes, it must justify them as bug fixes required to close Phase 0.
Acceptance Criteria
Phase 0.7 is accepted only if:
Phase 0 scope is audited
README status is accurate
docs/codex phase files exist through 0.7
validation commands are documented
make check passes
make test passes
make lint passes
make schema passes
makemigrations --check --dry-run reports no changes
no new migration is created unless explicitly justified and approved
no new dependency is added
no business domain implementation is added
no React is added
no apps/web folder is added
no JWT or token auth is added
next phase is clearly identified as Phase 1 — Runtime Config + Minimal Onboarding
Validation Commands
Run from repository root:
make check
make test
make lint
make schema
Run migration check:
cd apps/api
uv run python manage.py makemigrations --check --dry-run
Optional direct checks:
cd apps/api
uv run python manage.py check
uv run pytest
uv run ruff check .
uv run python manage.py spectacular --file schema.yml
