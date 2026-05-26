# Houston — Agent Instructions

## Project

Houston is a B2B mobile-first Web App / PWA for field teams in hotels, restaurants, and retail.

MVP pilot: Mama Shelter Nice.

Core operational loop:

Observation → Signal → Action → Execution → Validation → Feed update.

## Stack

Backend:
- Python 3.14.2
- Django 5.2 LTS
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Django Channels
- drf-spectacular
- pytest
- Ruff
- uv

Frontend MVP:
- Django Templates
- HTMX
- TypeScript targeted modules only
- Vite only for TypeScript/CSS bundling if needed
- Alpine.js or Stimulus only if needed
- PWA manifest
- minimal service worker

Architecture:
- Modular monolith
- Domain-oriented Django apps
- Event-driven internal architecture
- Transactional outbox pattern later
- No microservices before MVP validation
- No React SPA for MVP

## Backend target structure

apps/api/
├── config/
└── houston/
    ├── core/
    ├── accounts/
    ├── organizations/
    ├── establishments/
    ├── observations/
    ├── signals/
    ├── actions/
    ├── checklists/
    ├── comments/
    ├── notifications/
    ├── realtime/
    ├── ai/
    ├── events/
    └── uploads/

## Rules

- Do not create a React SPA.
- Do not create apps/web.
- Use Django Templates for product screens.
- Use HTMX for partial updates.
- Use TypeScript only for isolated frontend modules.
- DRF is used for JSON APIs where needed, not for every product screen.
- Do not build generic CRUD-first APIs.
- APIs expose product workflows and authorized domain commands.
- Business logic must not live in views/controllers.
- Views call application services.
- Models contain fields, relationships, constraints, and simple invariants only.
- Use selectors/query modules for read-side/feed logic.
- Important business mutations must emit application events later.
- AI never writes directly to core business tables.
- Backend validates every AI output before persistence.
- Visibility and permissions are always resolved server-side.
- WebSocket subscriptions must be authorized server-side.
- Realtime payloads are minimal and trigger partial refetch.
- Use UUID primary keys.
- Use PostgreSQL as the source of truth.
- Uploads are backend-mediated in the MVP.
- No direct-to-storage signed uploads in MVP.
- No raw Observation text in realtime payloads, notifications, logs, or unauthorized APIs.
- Tests are required for domain services, permissions, API workflows, feed queries, and AI contracts.

## Definition of done

A task is done only when:
- tests pass
- lint passes
- Docker Compose boots
- health endpoint returns 200
- OpenAPI schema is generated
- README explains local commands
- the diff stays scoped to the requested phase