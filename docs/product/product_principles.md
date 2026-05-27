# Product Principles

Status: authoritative
Last reviewed: 2026-05-27

## 1. Product Identity

Houston is not a generic ticketing tool or a CRUD admin app.

Houston is a structured operational workflow system for field teams. It turns field input into supervised operational follow-up with backend-owned rules, explicit state transitions, and clear accountability.

## 2. Core Product Loop

Houston follows this operational loop:

```txt
Observation → AI Pipeline → Signal → Action → Execution → Validation → Feed/Notification update
```

The product is built to make this loop reliable, visible, and usable in real field conditions.

## 3. Non-Negotiable Principles

- Backend owns business rules.
- Frontend is an interaction layer, not business authority.
- PostgreSQL stores business truth.
- OpenAPI is the API contract.
- AI proposes, backend validates, humans control authority.
- Observation, Signal, Action, Checklist, Chat, Comment, and Notification are distinct concepts.
- Chat must not replace structured operational workflows.
- Realtime coordinates refetch and lightweight updates; it does not own business truth.
- Permissions are backend-enforced.
- Tenant and establishment scoping are mandatory.
- Sensitive content must be minimized in logs, notifications, and realtime payloads.

## 4. AI Principles

- AI never mutates the database directly.
- AI output must be backend-validated.
- AI does not decide permissions.
- AI does not create Actions in MVP.
- AI does not analyze Chat in MVP.

## 5. Communication Principles

- Operational work belongs in Observations, Signals, Actions, and Checklists.
- Free-form exchange belongs in Establishment General Chat.
- Chat is independent in MVP.
- Comments are contextual, while Chat is general.

## 6. MVP Discipline

- Build the smallest complete operational loop.
- Avoid premature generic abstractions.
- Mark future scope as candidate.
- Prefer clear product invariants over over-detailed implementation rules.
