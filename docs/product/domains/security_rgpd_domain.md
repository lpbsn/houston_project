# Security / RGPD Domain

Status: authoritative
Last reviewed: 2026-05-27
Implementation status: partial

## 1. Purpose

This domain defines Houston's MVP product-level privacy, security, and RGPD/GDPR baseline for data minimization, sensitive-content handling, media privacy, AI data handling, logging boundaries, retention principles, and high-level incident and DSAR expectations.

Identity / Membership defines who the user is and which establishment they belong to. RBAC / Permissions defines what an authenticated member can see and do. This document defines how sensitive data must be handled once access rules apply.

## 2. MVP Scope

- Controller/processor positioning for operational data vs platform/security data.
- Establishment isolation and backend authorization as mandatory security boundaries.
- Data minimization, purpose limitation, and retention limitation at product level.
- Raw Observation privacy boundaries across feeds, notifications, realtime, logs, and frontend state.
- Private media principles for photos and temporary audio handling.
- AI input/output privacy boundaries: only validated pipeline inputs may be sent to AI; Chat and images are excluded from AI analysis in MVP.
- Minimal technical logging, minimal notification payloads, and minimal realtime payloads.
- High-level incident handling and DSAR/export/delete expectations only.

## 3. Out of Scope

- Product implementation of a DPA workflow, full legal compliance manual, DPIA procedure UI, or subprocessor register UI.
- Self-service privacy portal, admin privacy console, or full data export UI.
- Exact infrastructure runbook, vendor tooling, or provider-specific privacy guarantees not validated in current code or contracts.
- BYOK or per-establishment AI keys.
- Arbitrary support/admin raw-data browsing.
- Medical-grade, legal-grade, or broad compliance guarantees.

## 4. Core Invariants

- Collect only data needed for the operational workflow.
- Process data only for validated product purposes.
- Establishment isolation is mandatory.
- Backend authorization is required before returning business data or granting business actions.
- Security controls fail closed.
- A processor agreement / DPA is a legal/business prerequisite for real client operation, but not a product feature in MVP.
- Raw Observation text is sensitive operational input and must not appear in feeds, notifications, realtime payloads, technical logs, or persistent frontend storage.
- Media is private operational context and must never be public by default.
- Notifications and realtime payloads are minimal and do not grant access.
- AI only receives validated in-scope inputs; Chat is not analyzed in MVP; images are not sent to AI in MVP.
- AI never writes business truth directly.
- Technical logs must not contain raw Observation text, full comments, chat body, audio, photos, tokens, secrets, or full AI prompt/content.
- Retention is limited by purpose; exact durations are candidate unless separately validated.

## 5. Main Objects

- `ProcessingRole`
  - The client is controller for operational data.
  - Houston/FloorPower is processor for operational processing.
  - Houston/FloorPower may be controller for platform/account/security/support/technical-log data.

- `DataCategory`
  - Account and session data.
  - Membership, role, and operational-domain context.
  - Operational content: observations, media, comments/chat, notifications.
  - Technical/security traces and AI metadata.

- `SecurityControl`
  - Backend access control and tenant isolation.
  - Minimal payloads and private media handling.
  - Secure logging and fail-closed defaults.

- `RetentionRule`
  - Keep only what is needed for operational, legal, or security purpose.
  - Exact durations are not validated here.

- `Audit and Security Log`
  - Technical or security trace used for investigation.
  - Must avoid business content.

- `Incident`
  - Suspected security issue or personal-data issue requiring assessment and containment.

## 6. Lifecycle / Statuses

Not applicable as a business lifecycle in MVP. Security/RGPD applies continuously across authentication, authorization, data handling, media, AI, notifications, realtime, logging, and support.

Incident assessment, containment, export, deletion, and anonymization workflows are candidate unless validated in code or schema.

## 7. Permissions

- Normal users access only authorized establishment data through active membership and backend checks.
- Detailed role and action matrices remain in `identity_membership_domain.md` and `rbac_permissions_domain.md`.
- Media access requires backend authorization. Signed URL behavior is a candidate target unless confirmed by current code and `apps/api/schema.yml`.
- Notifications, realtime signals, and frontend visibility never grant access.
- Cross-tenant access is forbidden.
- Support/admin access is not validated as a public product API. Any future access must be least-privilege, limited, and logged.
- Logs and audit traces must not expose sensitive business content.

## 8. Events

No Security / RGPD-specific event contract is validated in current code or in `apps/api/schema.yml`.

Current code validates a generic `EventEnvelope` with categories such as `technical`, `ai`, and `audit`, but this does not prove that a security event catalog is implemented.

Candidate events only:

- `SecurityEventRecorded` candidate
- `SupportAccessGranted` candidate
- `SupportAccessRevoked` candidate
- `PersonalDataBreachSuspected` candidate
- `PersonalDataBreachAssessed` candidate
- `DataExportRequested` candidate
- `DataDeletionRequested` candidate
- `MediaDeleted` candidate
- `AudioDeletedAfterTranscription` candidate
- `AIRequestLogged` candidate, metadata only

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented endpoints confirmed in `apps/api/schema.yml`:

- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/bootstrap/`

Implemented security truths confirmed today:

- Login, refresh, and logout are CSRF-protected.
- Bootstrap is bearer-authenticated.
- Auth responses expose backend-approved membership context.
- No export, delete, privacy, media, support, or security-admin endpoint is currently confirmed as implemented.

Candidate endpoints only:

- Media signed URL endpoint
- Data export request endpoint
- Data deletion or offboarding endpoint
- Incident reporting endpoint
- Support or audit access endpoint
- Retention or privacy admin endpoint

## 10. Frontend Expectations

- Frontend must not persist access tokens or sensitive operational content to durable browser storage.
- TanStack Query owns server state. Auth bootstrap data must clear on logout or session loss.
- Frontend fetches full content only through authenticated and authorized API calls.
- Frontend must not rely on notification payloads or realtime payloads as business truth.
- Frontend must not display raw Observation text in feed cards or from notification/realtime payloads.
- Frontend must not store audio durably.
- Frontend should keep any raw Observation draft behavior minimal and short-lived.
- Frontend must handle `401`, `403`, and `404` without turning UI hints into security authority.

## 11. AI Agent Notes

- Inspect current code before claiming a security control is implemented.
- Inspect `apps/api/schema.yml` before listing privacy/security endpoints.
- Read `identity_membership_domain.md` and `rbac_permissions_domain.md` before changing access rules.
- Do not log raw Observation text, chat body, full comments, audio, photos, tokens, secrets, or AI prompt/content.
- Do not expose raw Observation text in feed, notification, realtime, or persistent frontend state.
- Do not send images to AI in MVP.
- Do not analyze Chat with AI in MVP.
- Do not describe Houston as GDPR-compliant by default; describe implemented or candidate controls only.
- Do not invent GDPR compliance guarantees.
- Do not invent support/admin raw-data browsing.
- When adding sensitive endpoints later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
