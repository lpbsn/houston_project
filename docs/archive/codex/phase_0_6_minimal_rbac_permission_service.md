# Phase 0.6 — Minimal RBAC / Permission Service Foundation

## Status

Planned.

## Context

Houston Phase 0 has already established the technical and identity foundation.

Validated previous phases:

- Phase 0.1 — Foundations
- Phase 0.2 — Foundation Hardening
- Phase 0.3 — Core Technical Primitives
- Phase 0.4 — Identity & Access Foundation
- Phase 0.5 — Web Auth Foundation, pending final full test validation if PostgreSQL/Docker was unavailable during implementation

Phase 0.5 introduced or is expected to introduce:

- Django session authentication
- `/login/`
- `/logout/`
- protected `/app/`
- current establishment context resolution
- safe establishment selection through session context
- app access blocked for users without valid active membership

Phase 0.6 must now add the smallest useful permission foundation before any business domain is implemented.

This phase is not a full RBAC product.

It is a minimal backend permission service foundation.

## Mandatory Reading Before Planning

Before producing any plan or modifying implementation files, Codex must inspect the existing repository.

Codex must not rely only on this phase document or on assumptions.

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

`Repository And Cadrage Facts Inspected`

This section must list:

- each repository file inspected
- each product / cadrage document inspected
- relevant product constraints found
- relevant technical constraints found
- exact enum names discovered for:
  - `User.identity_type`
  - `User.status`
  - `Organization.status`
  - `Establishment.status`
  - `EstablishmentMembership.role`
  - `EstablishmentMembership.status`
- current access context design from Phase 0.5
- current URL structure
- current test structure
- whether existing factories or fixtures exist
- conflicts or ambiguities between the phase scope and cadrage documents

If Codex does not include this section, the plan must be rejected.

## Business Goal

Prepare the backend authorization foundation before building operational domains.

Houston must eventually support different access levels for:

- Owner
- Director
- Manager
- Staff

But Phase 0.6 must only implement the minimal permission service needed to keep future business features safe.

The goal is to answer simple questions such as:

- Can this user access the app?
- Can this user manage establishment settings?
- Can this user manage memberships?
- Can this user manage runtime configuration?
- Can this user view operational feeds?
- Can this user create observations?
- Can this user create actions?
- Can this user validate actions?
- Is this user limited to specific operational domains?

## Technical Goal

Create a small, tested permission layer based on existing models.

The permission layer must be:

- backend-owned
- explicit
- hard-coded for MVP
- role-based
- establishment-scoped
- tested
- simple to call from future views/services

It must not introduce a dynamic permissions database.

## In Scope

### Permission service/helper

Add a minimal permission service.

Recommended location:

- `apps/api/houston/establishments/permissions.py`

Alternative acceptable location:

- `apps/api/houston/accounts/permissions.py`

Codex must justify the chosen location in the plan.

The service should expose simple permission functions.

Possible API:

- `can_access_app(membership) -> bool`
- `can_manage_establishment_settings(membership) -> bool`
- `can_manage_memberships(membership) -> bool`
- `can_manage_runtime_context(membership) -> bool`
- `can_view_signal_feed(membership) -> bool`
- `can_create_observation(membership) -> bool`
- `can_create_action(membership) -> bool`
- `can_validate_action(membership) -> bool`
- `can_access_domain(membership, domain_key: str) -> bool`

The final function names may differ if Codex proposes a cleaner convention, but they must remain simple and explicit.

### Role behavior

Use existing `EstablishmentMembership.role` enum values.

Do not invent new roles.

Expected MVP direction:

- Owner:
  - broad establishment administration permissions
  - can manage memberships
  - can manage establishment settings
  - can manage runtime context
  - can access all operational domains
- Director:
  - broad operational and management permissions
  - can manage managers/staff depending existing cadrage
  - can access all operational domains
- Manager:
  - operational management permissions
  - can create actions
  - can validate actions
  - domain access may be restricted by `operational_domains`
- Staff:
  - execution/field permissions
  - can create observations
  - can view assigned or relevant execution scope later
  - no establishment administration permission

Phase 0.6 does not need to fully enforce every future product rule.

It must only create the minimal permission foundation.

### Domain access

Use `EstablishmentMembership.operational_domains`.

Recommended rule:

- Owner and Director can access all domains
- Manager and Staff use `operational_domains`
- if `operational_domains` is empty:
  - do not guess broad access unless explicitly justified by the product docs
  - Codex must propose and justify the exact rule in the plan

No domain model should be created in this phase.

Domains remain string keys for now.

### Integration with current access context

If Phase 0.5 created a current access context helper, Phase 0.6 may lightly integrate with it.

For example:

- expose current membership to permission calls
- add simple permission checks to `/app/`
- keep app blocking behavior consistent

Do not create complex middleware.

Do not refactor Phase 0.5 heavily unless necessary.

### Tests

Add unit tests for permission behavior.

Tests must cover:

- Owner permissions
- Director permissions
- Manager permissions
- Staff permissions
- inactive membership denied
- inactive/suspended user denied if relevant through current access context
- domain access for Owner/Director
- domain access for Manager/Staff with matching domain
- domain access denied for Manager/Staff without matching domain
- empty operational domains behavior
- unknown role/status handling if applicable

Tests must use existing fixtures/factories if they exist.

If no factories exist, create minimal pytest fixtures inside the relevant test module or local `conftest.py`.

Do not introduce Factory Boy unless already present or explicitly approved.

## Out of Scope

Do not implement:

- JWT
- refresh tokens
- API token auth
- DRF login endpoint
- invitation flow
- signup flow
- password reset
- email verification
- magic links
- SSO
- MFA
- dynamic permission tables
- custom role model
- role management UI
- permission management UI
- full RBAC matrix engine
- policy framework dependency
- django-guardian
- rules
- casbin
- object-level permissions package
- Observation
- Signal
- Action
- Checklist
- Comments
- Notifications
- Realtime
- Celery jobs
- Channels consumers
- AI pipeline
- Uploads
- React
- TypeScript
- `apps/web`

## Architecture Constraints

Keep the implementation small.

Prefer simple functions over classes unless a class is clearly better.

Prefer explicit permission functions over generic magic.

Do not add dependencies.

Do not create new database tables.

Do not create migrations.

Do not introduce a permission DSL.

Do not introduce policy objects unless the repository already has that convention.

Do not create abstractions for future needs unless directly used by this phase.

This phase should require no migrations.

If Codex believes a migration is required, it must explain why in the plan before implementation.

## Existing Repository Facts To Respect

Current known repository facts:

- Django app path is `apps/api`
- URL root is `apps/api/config/urls.py`
- Existing root page uses `HomeView` from `houston.core.views`
- Existing API health route is under `api/v1/health/`
- `AUTH_USER_MODEL = "accounts.User"`
- Phase 0.5 may have added:
  - `apps/api/houston/accounts/views.py`
  - `apps/api/houston/accounts/forms.py`
  - `apps/api/houston/establishments/access.py`
  - protected app view in `apps/api/houston/core/views.py`
  - login template
  - app home template
- Tests currently live under app-level folders such as:
  - `apps/api/houston/accounts/tests/`
  - `apps/api/houston/core/tests/`
  - `apps/api/houston/organizations/tests/`
  - `apps/api/houston/establishments/tests/`
- `Makefile` validation commands use Docker Compose:
  - `make check`
  - `make test`
  - `make lint`
  - `make schema`

Codex must verify these facts before planning.

## Expected Files

Codex may need to modify or create files similar to:

- `apps/api/houston/establishments/permissions.py`
- `apps/api/houston/establishments/tests/test_permissions.py`
- `apps/api/houston/core/views.py` only if lightly integrating `/app/`
- `apps/api/houston/core/tests/test_app_home.py` only if existing app access behavior must be extended
- `README.md` only if a small usage note is necessary

Actual paths must follow the existing project structure.

Codex must inspect the repository before deciding exact files.

## Implementation Guidance

### Permission function style

Prefer this style:

```python
def can_manage_memberships(membership) -> bool:
    ...
or a small namespaced alternative.
Avoid this in Phase 0.6:
class PermissionEngine:
    ...
unless Codex strongly justifies it.
Membership validity
Every permission must deny access if:
membership is missing
membership is not active
related user is missing
related user is not active, if the function has access to user status
If the permission function only receives a membership, it should still use membership status.
Role mapping
Use existing enum values from EstablishmentMembership.Role.
Do not compare against guessed strings if enum constants exist.
Domain access
For can_access_domain(membership, domain_key):
deny if membership inactive
deny if domain key is blank
allow Owner/Director all domains
for Manager/Staff, check operational_domains
define exact behavior for empty operational_domains and test it
Current access context
Do not duplicate Phase 0.5 access context logic.
Reuse it where relevant.
If Phase 0.5 already has an access context object, Codex may add permission helpers that accept that context, but only if simple.
Acceptance Criteria
Phase 0.6 is accepted only if:
a minimal permission service exists
permission functions are explicit and easy to call
permissions are based on existing EstablishmentMembership role/status
no dynamic permission tables are created
no migrations are created
no dependencies are added
domain access behavior is defined and tested
Owner/Director/Manager/Staff behavior is tested
inactive membership is denied
app access behavior remains intact
pytest passes
ruff passes
Django check passes
OpenAPI schema generation still passes
no React is added
no apps/web folder is added
no JWT or token auth is added
no Observation/Signal/Action domain code is added
Validation Commands
Run from repository root:
make check
make test
make lint
make schema
Optional direct commands:
cd apps/api
uv run python manage.py check
uv run pytest
uv run ruff check .
uv run python manage.py spectacular --file schema.yml
Commit Rule
Do not commit until:
Phase 0.5 has passed the full validation gate
Phase 0.6 plan has been reviewed
implementation has been reviewed
tests pass
lint passes
schema generation passes
no out-of-scope files or domains were added
Suggested commit message:
git commit -m "Add minimal RBAC permission foundation"
Final response:
confirm the file was created
list any required source file that was missing
do not implement anything else
