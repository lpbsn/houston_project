# Observation Domain

Status: authoritative
Last reviewed: 2026-06-01
Implementation status: implemented (Phase 3 MVP — submit + processing queued; pipeline Phase 4)

## 1. Purpose

This domain defines Houston's raw field input submission boundary.

Observation owns:
- raw user-validated field input
- submit-time validation and persistence boundary
- handoff into the processing pipeline after persistence
- the business distinction between raw Observation and structured Signal

Observation does not own:
- media lifecycle, access, or cleanup
- transcription contracts or AI pipeline contracts
- Signal lifecycle or aggregation rules
- Checklist lifecycle
- RBAC internals
- Security / RGPD policy details

The processing pipeline may use AI, but Observation does not own AI contracts or provider behavior.

## 2. MVP Scope

- Direct Observation submit from the reporting flow.
- Typed text input.
- Validated transcription text input.
- Optional photos through Upload / Media, up to 3 photos per Observation.
- Immediate persistence on submit, before downstream processing completes.
- Processing enqueue after persistence.
- Local-only frontend draft before submit.
- Simplified post-submit feedback for analysis progress and outcome.
- Candidate: checklist-origin Observation flow and checklist context linkage, including fields such as `checklist_execution_id` and `checklist_task_execution_id`, when validated in the Checklist and API layers.

## 3. Out of Scope

- Backend drafts.
- Editing an Observation after submit.
- Normal-user deletion of submitted Observations.
- Anonymous reporting.
- User-declared urgency.
- Photo-only Observation submit.
- Observation detail page in normal product UI.
- Raw Observation display in feeds, Signal detail, notifications, or realtime payloads.
- AI image analysis.
- Persistent audio as Observation media.
- Observation-as-ticket behavior.

## 4. Core Invariants

- Observation is raw user-validated field input.
- Observation is not a Signal, Action, or ChecklistTask.
- Observation is persisted on submit and remains unique even if later processing creates or aggregates Signals.
- Text is required as typed input or validated transcription text; photo-only Observation is forbidden.
- Target validation is 10 to 1,000 characters; a shorter checklist-origin text is candidate only when validated checklist context supports it.
- Photos are optional and follow Upload / Media rules.
- Audio is temporary; only validated transcription text persists in MVP.
- Images are not sent to AI in MVP.
- Observation enters the AI pipeline only after persistence.
- Only structured Signals enter operational feeds.
- Raw Observation text may be used internally by the authorized backend processing pipeline, but must not leak into normal product UI, feeds, notifications, realtime payloads, technical logs, or durable frontend storage.
- Raw Observation text must not appear in normal product UI, feeds, notifications, realtime payloads, technical logs, or durable frontend storage.
- Processing failure must not delete the submitted Observation.
- **One Observation may yield zero, one, or many Signals** after backend validation of AI pipeline output; each Signal carries **one** primary module/domain/subject categorization (see [`signal_domain.md`](signal_domain.md), [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)).
- Distinct problems described in one Observation must produce **multiple CandidateSignals**, never multiple categorizations on a single Signal.

## 5. Main Objects

- `Observation`
  - Raw user-validated field input submitted by an authenticated member in an establishment context.
  - The persisted handoff point between field reporting and downstream processing.

- `ObservationProcessing`
  - Technical processing state for the submitted Observation.
  - Backend/admin concern that should be simplified for normal users.

- `ObservationOutcome`
  - Business result after processing, such as Signal creation, aggregation, or no structured Signal.
  - Separate from the raw Observation itself.
  - Plural outcomes (`signals_created`) are normal when one Observation describes multiple distinct problems.

- `ObservationMedia`
  - Optional photo media linked through Upload / Media.
  - Owned here only as a relationship boundary, not as a media lifecycle contract.

- `ObservationOrigin`
  - Source context for the submission, such as direct reporting.
  - Candidate: checklist-origin context and related linkage fields when that flow is implemented.

- `LocalObservationDraft`
  - Frontend-only draft state before submit.
  - Not backend authority and not a persisted business object.

## 6. Lifecycle / Statuses

- User-facing lifecycle in MVP:
  - `draft` local only
  - `submitted` or persisted
  - simplified analysis pending, complete, or temporary problem messaging

- Candidate technical processing statuses:
  - `queued`
  - `processing`
  - `processed`
  - `retrying`
  - `failed`

- Candidate processing outcomes:
  - `signal_created`
  - `signals_created`
  - `signal_aggregated`
  - `no_signal_created`
  - `not_actionable`

See [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md) for CandidateSignal shape and segmentation rules.

- Processing statuses and outcomes are candidate until implemented in code and exposed through OpenAPI where applicable.

- Candidate lifecycle notes:
  - no post-submit edit in MVP
  - no backend draft in MVP
  - no Signal created is a valid normal outcome
  - up to 5 generated Signals per Observation is a candidate limit

## 7. Permissions

- Active authorized establishment members may submit Observations if RBAC allows.
- Observation creation must be validated as an establishment-scoped backend permission; current permission helpers must be inspected before assuming the exact rule.
- Raw Observation text is not visible in normal product UI.
- Resulting Signals, not raw Observations, are the normal supervised product surface.
- Any exceptional raw Observation access must remain backend-authorized and follow Security / RGPD constraints.
- No anonymous Observation submission is allowed.
- Candidate: checklist-origin Observation requires authorized access to the originating checklist context.

## 8. Events

No Observation event contract is validated in current code or in `apps/api/schema.yml`.

Candidate events only:
- `ObservationCreated`
- `ObservationMediaLinked`
- `ObservationQueuedForAI`
- `ObservationProcessingStarted`
- `ObservationProcessingSucceeded`
- `ObservationProcessingFailed`
- `ObservationProcessingRetried`
- `ObservationLinkedToSignal`
- `ObservationMarkedNotActionable`
- `ObservationOutcomeRecorded`
- `ObservationDraftDiscarded` frontend-only candidate

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Implemented endpoints confirmed in `apps/api/schema.yml`:
- `POST /api/v1/establishments/{establishment_id}/observations/` — submit with `text` (maps to internal `raw_text`) and optional `temporary_upload_ids`; response includes `id`, `submitted_at`, `media_count`, `processing_status` only (no raw text).

Candidate API capabilities only:
- submit checklist-origin Observation
- `GET` processing status (deferred; submit returns `processing_status=queued` in Phase 3)
- internal or admin retry processing command (Phase 4+)

Upload, transcription, and media endpoints are documented in [`upload_media_domain.md`](upload_media_domain.md).

## 10. Frontend Expectations

- The reporting flow should support typed text, editable transcription text, and optional photos.
- Frontend should block obvious invalid states such as photo-only submit, but backend validation remains authoritative.
- Draft state is local only and should clear after successful submit.
- Backend draft does not exist in MVP.
- Submit success means the Observation was persisted, not that a Signal is already ready.
- UI should show simplified analysis feedback rather than backend technical statuses.
- UI must not expose raw Observation text in feeds, Signal detail, notifications, realtime payloads, or durable frontend storage.
- TanStack Query owns server state for implemented APIs.
- Frontend must use generated OpenAPI clients only for endpoints present in `apps/api/schema.yml`.

## 11. AI Agent Notes

- Inspect current code before claiming Observation models, services, events, or endpoints exist.
- Inspect `apps/api/schema.yml` before listing any Observation API as implemented.
- Inspect Upload / Media before changing photo or audio rules.
- Inspect AI documentation and [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md) before changing transcription or processing contracts.
- Inspect Signal documentation before changing create, aggregate, or outcome behavior.
- Inspect Checklist documentation before changing checklist-origin context.
- Inspect Security / RGPD before changing raw-text visibility, logging, retention, notification, or realtime rules.
- Inspect RBAC / Permissions before changing who may submit or access related resources.
- Keep the photo limit aligned with `upload_media_domain.md`.
- Do not make Observation a ticket, a Signal, or a visible operational feed object.
- Do not invent backend drafts, urgency input, anonymous reporting, image-to-AI behavior, or persistent audio media.
- Do not expose raw Observation text in normal product UI, feeds, notifications, realtime payloads, or persistent frontend storage.
- When Observation APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
