# Codex Task — Phase 0.4 Identity & Access Foundation

Read AGENTS.md first.

## Goal

Add the minimal identity and access foundation for Houston.

This phase creates the core identity tables needed before implementing product workflows.

## Product decisions

Houston uses:

- A global User.
- Organization owns Establishments.
- EstablishmentMembership links a User to an Establishment.
- Role, operational domains, and membership status live on EstablishmentMembership.
- Most users will have one membership, but the data model must support multiple establishments.

## Scope

Allowed changes:

1. Custom User model

Create a custom User model in `houston.accounts`.

Use Django's `AbstractUser` as base unless there is a strong reason not to.

Required fields:
- UUID primary key
- email optional at database level because Staff may use username identity
- identity_type enum:
  - email
  - username
- status enum:
  - pending
  - active
  - suspended
  - anonymized
- timestamps via core BaseModel if compatible

Rules:
- Email identity is required for Owner/Director/Manager later, but do not implement role-based validation yet.
- Username identity is allowed for Staff later.
- Do not implement login logic yet.
- Do not implement token logic yet.

2. Organization model

Create minimal Organization model in `houston.organizations`.

Fields:
- UUID primary key
- name
- status enum:
  - active
  - suspended
  - archived
- timestamps

3. Establishment model

Create minimal Establishment model in `houston.establishments`.

Fields:
- UUID primary key
- organization FK
- name
- status enum:
  - draft
  - active
  - deactivated
- timestamps

4. EstablishmentMembership model

Create EstablishmentMembership in `houston.establishments` or `houston.accounts`.

Choose the most coherent location and explain the choice.

Fields:
- UUID primary key
- user FK
- establishment FK
- role enum:
  - owner
  - director
  - manager
  - staff
- status enum:
  - invited
  - active
  - deactivated
- operational_domains as JSONField default list
- timestamps

Constraints:
- unique user + establishment membership
- useful indexes for establishment, user, role, status

5. Settings

Set:

```python
AUTH_USER_MODEL = "accounts.User"
or the correct app label if different.
Admin
If Django admin is enabled, register the new models minimally.
Tests
Add tests for:
User UUID primary key
User identity_type/status choices
Organization creation
Establishment belongs to Organization
Membership links User + Establishment
Membership unique constraint
Membership role/status choices
operational_domains defaults to an empty list and is not shared between instances
Migrations
Create migrations only for:
accounts
organizations
establishments
No other app should get concrete models or migrations.
Constraints
Do not implement login.
Do not implement logout.
Do not implement JWT.
Do not implement refresh tokens.
Do not implement password reset.
Do not implement invitation accept flow.
Do not implement permissions matrix.
Do not implement Observation, Signal, Action, AI, uploads, notifications, realtime.
Do not add React.
Do not create apps/web.
Do not create product workflow endpoints.
Keep the diff small.
Acceptance
The following commands must pass:
docker compose exec api python manage.py check
docker compose exec api python manage.py makemigrations --check --dry-run
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api python manage.py spectacular --file schema.yml
make check
make test
make lint
make schema
Also verify created migrations:
find apps/api/houston -path "*/migrations/*.py" -not -name "__init__.py"
Expected:
migrations for accounts
migrations for organizations
migrations for establishments
no migrations for observations, signals, actions, AI, uploads, notifications, realtime