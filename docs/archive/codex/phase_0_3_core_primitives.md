# Codex Task — Phase 0.3 Core Technical Primitives

Read AGENTS.md first.

## Goal

Add minimal reusable technical primitives for the Houston Django modular monolith.

This phase prepares shared building blocks for future domains without implementing business features.

## Scope

Allowed changes:

1. Core abstract models
   - Add reusable abstract base models in `houston.core`.
   - Use UUID primary keys.
   - Add `created_at` and `updated_at` timestamps.
   - Keep models abstract only.
   - Do not create concrete business tables.

2. Domain errors
   - Add a minimal domain exception hierarchy.
   - Keep it generic and reusable.
   - Do not add domain-specific errors for Observation, Signal, Action, etc.

3. Service result pattern
   - Add a small typed result object for application services.
   - It should support success/failure, value, error code, and message.
   - Keep it simple.

4. Event envelope skeleton
   - Add a minimal event envelope dataclass or typed structure.
   - Do not implement persistence yet.
   - Do not create `application_events` table yet.
   - Do not add event dispatching/jobs yet.

5. Tests
   - Add unit tests for:
     - UUID base model behavior if testable without concrete business model.
     - service result success/failure helpers.
     - domain errors.
     - event envelope shape.

## Constraints

- Do not implement auth.
- Do not implement users, memberships, roles, permissions.
- Do not implement Observation, Signal, Action, AI, uploads, notifications, realtime.
- Do not create business models.
- Do not create database tables except Django default/system tables if already present.
- Do not create migrations for abstract-only models.
- Do not implement event persistence.
- Do not implement Celery jobs.
- Do not add React.
- Do not create apps/web.
- Keep the diff small.

## Suggested files

You may create or modify:

```txt
apps/api/houston/core/models.py
apps/api/houston/core/results.py
apps/api/houston/core/exceptions.py
apps/api/houston/core/events.py
apps/api/houston/core/tests/test_results.py
apps/api/houston/core/tests/test_exceptions.py
apps/api/houston/core/tests/test_events.py
apps/api/houston/core/tests/test_models.py
README.md if useful