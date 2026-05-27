# Product Operating Model

Status: authoritative
Last reviewed: 2026-05-27

## 1. Operating Model Summary

Houston helps a field team capture what is happening, structure it into an operational situation, assign execution, validate the outcome, and keep the establishment informed through feeds and notifications.

It is a backend-centric operating model: field input starts the loop, AI may assist with structuring, managers supervise decisions, staff executes work, and the backend remains the authority for workflow state, visibility, and permissions.

## 2. Main Actors

- Owner: organization-level governance and oversight.
- Director: establishment-level supervision.
- Manager: operational supervision, coordination, and validation.
- Staff: field participation, reporting, and execution.

Detailed permission matrices belong to domain docs, not this document.

## 3. Core Operational Flow

1. A user reports an Observation.
2. AI or transcription may help structure the input into validated text and proposals.
3. The AI pipeline proposes candidate Signals.
4. The backend validates the proposals against business rules and scope.
5. A Signal is created or aggregated into an existing Signal.
6. A Manager supervises the Signal.
7. A Manager creates an Action.
8. Staff accepts and executes the Action.
9. A Manager validates the result.
10. Feeds and notifications update.

## 4. Supporting Flows

- Onboarding and runtime configuration initialize an establishment with the minimum structure needed for operational use.
- Media uploads provide optional operational context around Observations and follow backend-controlled access rules.
- Checklists support recurring or personal operational routines and can produce contextualized Observations.
- Comments support contextual discussion attached to Signals or Actions.
- Notifications route attention when action or awareness is needed.
- Realtime invalidation coordinates refetch and lightweight refresh behavior.
- Establishment General Chat establishment level discussion and remains separate from the structured operational workflow in MVP.

## 5. Domain Boundaries

- Observation: raw field input.
- Signal: structured operational situation linked to as Observation
- Action: executable task linked to a Signal.
- Checklist: recurring or personal operational routine.
- Comment: contextual discussion attached to a workflow object.
- Notification: attention routing.
- Chat: free-form establishment discussion.
- AI: proposal and structuring layer, not authority.

## 6. Current MVP Operating Model

The validated MVP phase order is:

1. Phase 0 — Full-stack foundation ✅ completed
2. Phase 1 — Identity / Memberships / RBAC
3. Phase 2 — Runtime config / Onboarding minimal
4. Phase 3 — Observation / Media / Transcription
5. Phase 4 — AI Pipeline / Signal Feed
6. Phase 5 — Actions / Execution Feed
7. Phase 6 — Notifications
8. Phase 7 — Checklists
9. Phase 8A — Realtime invalidation foundation
10. Phase 8B — Establishment General Chat
11. Phase 9 — Hardening
12. Phase 10 — Pilot readiness

Phase 0 is completed. Later phases define the validated MVP target scope; operational endpoints remain candidate unless they are present in `apps/api/schema.yml`.

## 7. Out-of-Scope Operating Behaviors

- No billing MVP.
- No advanced analytics MVP.
- No direct chat-to-signal conversion MVP.
- No AI analysis of Chat MVP.
- No multi-establishment advanced UX unless already validated.
- No generic ticketing workflow.
