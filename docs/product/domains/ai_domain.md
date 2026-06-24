# AI Domain

Status: authoritative
Last reviewed: 2026-06-13
Implementation status: partial (transcription + observation pipeline v4 implemented — prompt/schema `ai_observation_pipeline_v4`, aggregation on `issue_focus`, golden corpus G01–G11 green; AI onboarding permanently removed from product)

## 1. Purpose

This domain defines Houston's AI boundary as a proposal, transcription, structuring, classification, and routing-support layer.

It owns:
- product-level AI provider abstraction requirements
- the high-level transcription boundary
- the high-level Observation pipeline proposal boundary
- structured AI output requirements for business-affecting responses
- backend validation requirements for every AI proposal
- retry, failure, fallback, and usage-logging principles
- AI privacy, safety, and authority constraints

It does not own:
- final business authority
- direct database mutation
- permissions or RBAC decisions
- Observation submission validity
- Signal lifecycle or Action lifecycle
- Upload / Media lifecycle
- Chat behavior
- full provider implementation details
- full prompt text libraries
- detailed contract JSON schemas

## 2. MVP Scope

- Audio-to-editable-text transcription support before Observation submit.
- AI Observation pipeline proposals from validated Observation text only (contract: [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)).
- Onboarding runtime setup is **Manual V2 only** — AI onboarding is **permanently removed** from Houston (see [`runtime_config_onboarding_domain.md`](runtime_config_onboarding_domain.md)).
- Structured outputs for business-affecting AI responses, with strict backend-side validation before any business persistence.
- Product-level expectation that provider/model choices remain abstracted and replaceable, even though current code does not validate a concrete implementation yet.
- Metadata-oriented AI usage tracking and safe failure handling principles.
- Fallback expectations: manual text entry for transcription and safe retry or failure handling for the Observation pipeline.
- Observation pipeline may propose zero, one, or multiple **CandidateSignals**, each with **one** BusinessUnit / ActivitySubject classification; a multi-problem Observation yields multiple candidates (see [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)).
- AI must not receive image input in MVP.
- AI does not analyze Chat in MVP.

## 3. Out of Scope

- AI-assisted onboarding (removed permanently from Houston).
- AI direct writes to business tables.
- AI-created Actions.
- AI-decided permissions.
- AI-decided urgency in MVP.
- AI analysis of Chat.
- AI image analysis.
- Autonomous agents taking business actions without backend validation.
- BYOK or per-establishment AI keys in MVP unless later validated.
- Prompt-management UI or provider-routing UI.
- User-visible confidence-score authority in MVP.
- Fine-tuning on customer business content.
- Long-term storage of raw prompts or raw model content.
- AI-generated notifications without backend validation.
- AI access to arbitrary database context.

## 4. Core Invariants

- AI proposes; backend validates; humans control structural and operational authority.
- AI output is never trusted as business truth without backend validation.
- AI never mutates the database directly.
- AI does not decide permissions.
- AI does not create Actions in MVP.
- AI must not decide urgency in MVP.
- AI does not analyze Chat in MVP.
- AI must not receive image input in MVP.
- Audio is temporary and exists only to produce editable transcription text before validated text handoff.
- The Observation pipeline receives validated text only.
- The Observation pipeline must not receive audio files, images, temporary upload objects, or Chat content in MVP.
- Every structuring call must use an explicit schema or equivalently strict output contract.
- Every structured output must be checked against backend business rules before persistence.
- AI output may be consumed by backend services, but only after schema validation, business validation, and authorization checks where relevant.
- Standard technical logs must not contain clear-text prompts or raw model content.
- AI usage tracking stores technical metadata only and must avoid sensitive business payloads.
- AI failures must fail closed and must not corrupt business state.
- Provider and model choices must remain replaceable unless current code later validates a fixed implementation.

## 5. Main Objects

- `AIProvider`
  - Product concept for the backend-controlled provider target used for transcription or structuring calls.
  - A concrete provider interface is not validated as implemented yet.

- `AIRequest`
  - One AI operation in a domain such as `transcription` or `observation_pipeline`.
  - Exact persisted request models are not validated yet.

- `AIUsageLog`
  - Technical metadata about an AI call.
  - Candidate fields include provider, model, prompt version, latency, token count, status, and cost estimate.

- `AITranscript`
  - Temporary transcription result returned as editable text before Observation submit.
  - It is not validated as a persisted standalone business object.

- `AIObservationPipelineResult`
  - Structured output with 0..N **CandidateSignals**, each one BU/AS classification.
  - Contract: [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md).

- `PromptVersion`
  - Version identifier for control text used by an AI flow.
  - Full prompt text storage does not belong in this domain reference.
  - Observation pipeline: `prompt_version` and `schema_version` are both `ai_observation_pipeline_v4`; recorded on `AIUsageLog`. Structured output requires `issue_focus` per candidate (v4).

- `AIError`
  - Safe technical failure state with normalized error metadata.
  - Raw provider error payloads must not become normal-user product output.

`AIRequest`, `AIUsageLog`, `AITranscript`, `AIObservationPipelineResult`, `PromptVersion`, and `AIError` are product concepts, not required database model names until implemented.

## 6. Lifecycle / Statuses

Not validated as implemented yet. Candidate lifecycles only:

- General AI request: `requested`, `processing`, `succeeded`, `failed`, `retried`, `abandoned` or `canceled` if later needed.
- Transcription UI states: `recording`, `uploading`, `transcribing`, `transcription_ready`, `transcription_failed`.
- Observation pipeline states: `queued`, `processing`, `retrying`, `processed`, `failed`.
- Candidate timeout targets only: transcription 10s, Observation pipeline 20s, until enforced by code/tests.

## 7. Permissions

- Backend RBAC and establishment scoping are mandatory before any AI call starts.
- AI receives only the minimum authorized context needed for the current operation.
- AI never grants access, roles, or permissions.
- Normal users should see simplified progress or failure states rather than raw technical AI diagnostics.
- Metadata-oriented failure visibility for admin or support is candidate only and must still avoid sensitive content by default.
- AI input excludes Chat content in MVP.
- Image input is excluded from AI input in MVP.
- AI usage records should remain establishment-scoped when such records are implemented.

## 8. Events

No AI event contract is validated as implemented today.

Current code only proves that the generic `EventEnvelope` category set includes `ai`; it does not validate an AI event catalog.

Candidate events only (**not implemented** — no emitters in `ai/` or `signals/` today):
- `AIRequestStarted`
- `AIRequestSucceeded`
- `AIRequestFailed`
- `AIRequestRetried`
- `TranscriptionStarted`
- `TranscriptionSucceeded`
- `TranscriptionFailed`
- `TranscriptionAudioDeleted`
- `ObservationPipelineStarted`
- `ObservationPipelineSucceeded`
- `ObservationPipelineFailed`
- `ObservationPipelineRetried`

## 9. API Surface

Current API truth is `apps/api/schema.yml`.

Confirmed in `apps/api/schema.yml`:

- Transcription: `POST /api/v1/establishments/{establishment_id}/transcriptions/` — multipart audio, `AIUsageLog` domain `transcription`, model configurable (`HOUSTON_AI_TRANSCRIPTION_MODEL`, default `gpt-4o-transcribe`).
- Observation pipeline: submit Observation → Celery processing → Signals (see [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)); processing status via observation processing-status endpoint.

Candidate capabilities only:

- metadata-only admin or support failure detail beyond current surfaces

## 10. Frontend Expectations

- Frontend must present AI as assistance and progress feedback, not as business authority.
- Transcription text must be editable before Observation submit.
- If transcription fails, the user must be able to retry or type text manually.
- UI must not present confidence as operational authority in MVP.
- UI must not expose raw technical AI errors to normal users.
- UI should simplify AI pipeline technical states when business-safe summary states are enough.
- Frontend must not route AI input from Chat content in MVP.
- Frontend must not send image input to AI in MVP.
- TanStack Query owns server state for any future AI APIs.
- Frontend must use generated OpenAPI clients only for routes confirmed in `apps/api/schema.yml`.

## 11. AI Agent Notes

- Inspect current code before claiming provider abstractions, logs, jobs, prompts, events, or AI endpoints exist.
- Inspect `apps/api/schema.yml` before claiming any AI API is available.
- Inspect `security_rgpd_domain.md` before changing logging, minimization, retention, or prompt/content handling.
- Inspect `upload_media_domain.md` before changing audio or image boundaries.
- Inspect `observation_domain.md` before changing pipeline input or submit-time validation assumptions.
- Inspect the Signal domain source of truth before changing Signal creation or aggregation assumptions.
- Inspect [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md) before changing Observation pipeline outputs or segmentation.
- Inspect [`runtime_config_onboarding_domain.md`](runtime_config_onboarding_domain.md) for onboarding boundaries (Manual V2 only — no AI onboarding).
- Do not reintroduce AI onboarding APIs or product flows.
- Do not invent provider privacy guarantees, zero-retention claims, or training guarantees without validated evidence.
- Do not treat schema-valid AI output as business-valid output.
- Do not let AI write business tables directly.
- Do not let AI decide permissions, create Actions, or decide urgency.
- Do not add BYOK or multi-provider routing UI to MVP scope unless explicitly requested and separately validated.
- When AI APIs are added later, update backend authorization, OpenAPI, generated clients, tests, and this document together.
