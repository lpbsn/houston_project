# Phase 0.5 — Web Auth Foundation

## Status

Planned.

## Context

Houston is a Django 5.2 LTS server-rendered web app / PWA foundation.

Current validated phases:

- Phase 0.1 — Foundations
- Phase 0.2 — Foundation Hardening
- Phase 0.3 — Core Technical Primitives
- Phase 0.4 — Identity & Access Foundation

Phase 0.4 introduced:

- Custom `User` model in `houston.accounts`
- `AUTH_USER_MODEL = "accounts.User"`
- UUID primary key for `User`
- `identity_type` on `User`
- `status` on `User`
- nullable / blank email on `User`
- `Organization`
- `Establishment`
- `EstablishmentMembership`
- role and status on `EstablishmentMembership`
- `operational_domains` on `EstablishmentMembership`

Phase 0.5 must now add the smallest useful web authentication foundation for a server-rendered app.

This phase is intentionally not a full authentication product.

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
- `apps/api/houston/organizations/models.py`
- `apps/api/houston/establishments/models.py`
- `apps/api/houston/core/views.py`
- `apps/api/houston/core/urls.py`
- `apps/api/houston/core/templates/core/home.html`
- `apps/api/houston/accounts/migrations/`
- `apps/api/houston/organizations/migrations/`
- `apps/api/houston/establishments/migrations/`
- existing tests under `apps/api/houston/`
- existing templates under `apps/api/houston/`

Codex must also read these Codex phase documents:

- `docs/codex/phase_0_1_foundations.md`
- `docs/codex/phase_0_2_foundation_hardening.md`
- `docs/codex/phase_0_3_core_primitives.md`
- `docs/codex/phase_0_4_identity_access_foundation.md`

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
  - `Establishment.status`
  - `EstablishmentMembership.role`
  - `EstablishmentMembership.status`
- current URL structure
- current template structure
- current test structure
- whether existing factories or fixtures exist
- conflicts or ambiguities between the phase scope and cadrage documents

If Codex does not include this section, the plan must be rejected.

## Business Goal

Allow an authenticated user to access the protected Houston app shell and resolve their current establishment context.

Target user flow:

1. User visits `/app/`
2. If unauthenticated, user is redirected to `/login/`
3. User logs in using Django session authentication
4. User reaches `/app/`
5. The system resolves active establishment access
6. If the user has exactly one active establishment membership, it is automatically selected
7. If the user has no active membership, the app blocks access cleanly
8. If the user has multiple active memberships, the app must not guess silently

## Technical Goal

Introduce minimal web session authentication and current access context resolution.

This phase supports future phases without implementing them prematurely.

## In Scope

### Web auth

Add minimal web login and logout using Django session authentication.

Expected routes:

- `GET /login/`
- `POST /login/`
- `POST /logout/`
- `GET /app/`

Use Django’s built-in session authentication primitives where possible.

Do not introduce JWT or token authentication.

### Protected app shell

Add a minimal protected `/app/` page.

The page only needs to prove:

- the user is authenticated
- current access context can be resolved
- the selected establishment is available to the template when applicable

### Current access context

Add a small helper/service for resolving the current access context.

Recommended location:

- `houston.establishments.selectors`
- or `houston.establishments.access`

Do not create a large permissions system.

The context resolver should answer:

- Who is the current user?
- Is the user authenticated?
- What are the user’s active memberships?
- What is the selected establishment?
- Does the user have zero, one, or multiple active memberships?

Recommended behavior:

- Anonymous user: no access context
- Authenticated non-active user: no app access
- Authenticated active user with zero active memberships: blocked access state
- Authenticated active user with one active membership: auto-select that establishment
- Authenticated active user with multiple active memberships:
  - do not silently guess
  - return a “selection required” state or display a minimal placeholder
  - do not build a full establishment switcher in this phase unless explicitly approved later

Session key recommendation:

- `current_establishment_id`

Only store the selected establishment id in session after verifying that the user has an active membership for that establishment.

### User and membership status checks

Use existing Phase 0.4 enums/constants.

Only users with active status should access `/app/`.

Only active memberships should grant establishment access.

If enum names differ from this document, inspect the existing models and use the actual current names.

Do not invent new statuses.

### Templates

Add minimal templates only.

Possible templates:

- `apps/api/houston/accounts/templates/registration/login.html`
- `apps/api/houston/accounts/templates/registration/logged_out.html` only if needed
- `apps/api/houston/core/templates/app/home.html`
- or another app-local template path if more coherent with existing structure

Keep styling minimal.

Do not introduce a frontend framework.

Do not add React.

Do not add an `apps/web` folder.

### Tests

Add pytest tests for the new auth behavior.

Minimum expected tests:

1. Anonymous user visiting `/app/` is redirected to `/login/`
2. Authenticated active user with one active membership can access `/app/`
3. Authenticated active user with one active membership gets the establishment auto-selected
4. Authenticated active user with no active membership does not get app access
5. Suspended or non-active user does not get app access
6. Logout ends the session
7. Multiple active memberships are not silently guessed
8. Invalid `current_establishment_id` in session is cleared or ignored safely

Tests should use existing fixtures/factories if they exist.

If no factories exist, create minimal pytest fixtures inside the test module or local app `conftest.py`.

Do not introduce Factory Boy unless already present or explicitly approved.

## Out of Scope

Do not implement:

- JWT
- refresh tokens
- API token auth
- DRF login endpoint
- mobile login API
- invitation flow
- signup flow
- password reset
- email verification
- magic links
- SSO
- MFA
- full RBAC matrix
- permissions services beyond the small current access context helper
- operational domain permissions
- establishment switcher UI beyond a minimal placeholder
- Observation
- Signal
- Action
- Checklist
- Comments
- Notifications
- Realtime
- Celery jobs
- Channels consumers
- React
- TypeScript
- `apps/web`

## Architecture Constraints

Keep the implementation small.

Prefer Django built-ins.

Do not create a complex service layer.

Do not create abstractions for future needs unless directly used by this phase.

Do not add dependencies unless strictly necessary.

Do not change the database schema unless absolutely required.

This phase should ideally require no new migrations.

If Codex believes a migration is required, it must explain why in the plan before implementation.

## Existing Repository Facts To Respect

Current known repository facts:

- Django app path is `apps/api`
- URL root is `apps/api/config/urls.py`
- Existing root page uses `HomeView` from `houston.core.views`
- Existing template is app-local: `apps/api/houston/core/templates/core/home.html`
- Existing API health route is under `api/v1/health/`
- `AUTH_USER_MODEL = "accounts.User"`
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

- `apps/api/config/settings.py`
- `apps/api/config/urls.py`
- `apps/api/houston/accounts/views.py`
- `apps/api/houston/accounts/urls.py`
- `apps/api/houston/accounts/forms.py` only if necessary
- `apps/api/houston/accounts/templates/registration/login.html`
- `apps/api/houston/establishments/access.py`
- `apps/api/houston/establishments/selectors.py`
- `apps/api/houston/core/views.py`
- `apps/api/houston/core/templates/app/home.html`
- app-level tests under `apps/api/houston/.../tests/`
- `README.md` only if a small usage note is necessary

Actual paths must follow the existing project structure.

Codex must inspect the repository before deciding exact files.

## Implementation Guidance

### Login

Use Django session authentication.

Prefer built-in Django auth views/forms unless the current custom `User` model requires a small adapter.

Do not implement a custom authentication backend unless truly necessary.

If the custom User model currently relies on Django’s `username` field, keep login compatible with Django’s default behavior for now.

Do not implement final “email or username identifier” authentication in this phase unless explicitly approved.

### App access

`/app/` must require authentication.

After authentication, resolve the current establishment context.

If exactly one active membership exists, store the establishment id in session and render the app shell.

If zero active memberships exist, return a clean blocked-access state.

If multiple active memberships exist, return a clean selection-required state.

Do not create the final establishment switcher unless explicitly approved.

### Current establishment session safety

Never trust `request.session["current_establishment_id"]` blindly.

Always verify:

- the user is authenticated
- the user is active
- the membership exists
- the membership is active
- the membership belongs to the selected establishment

If the session contains an invalid establishment id, clear it and resolve again.

## Acceptance Criteria

Phase 0.5 is accepted only if:

- `/login/` renders a login page
- valid credentials create a Django session
- `/logout/` ends the session
- `/app/` is protected
- unauthenticated users are redirected to `/login/`
- active authenticated users with one active membership can access `/app/`
- the single active establishment is auto-selected
- users with no active membership are blocked cleanly
- users with multiple active memberships are not silently assigned a random establishment
- inactive/suspended users cannot access the app shell
- tests cover the expected behavior
- `pytest` passes
- `ruff` passes
- no React is added
- no `apps/web` folder is added
- no JWT or token auth is added
- no Observation/Signal/Action domain code is added
- no unnecessary migration is created

## Validation Commands

Run from repository root:

```bash
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
Manual local check if needed:
cd apps/api
uv run python manage.py runserver
Then check:
/login/
/app/
logout behavior
