# AI Domain

Status: authoritative
Implementation status: implemented (transcription + observation pipeline **v6**; AI onboarding permanently removed). Pipeline contract: [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md).

## 1. Purpose

AI is a proposal, transcription, structuring, and routing-support layer. Backend validates; humans keep structural and operational authority.

Owns: provider abstraction requirements, transcription boundary, Observation pipeline proposal boundary, structured-output + backend-validation rules, retry/failure/usage-logging principles, privacy and authority constraints.

Does not own: business writes, RBAC, Observation submit validity, Signal or Action Plan lifecycle, Upload lifecycle, Chat, full prompt libraries, or detailed JSON schemas (those live in the pipeline contract).

## 2. Scope

In: audio → editable text before Observation submit; Observation pipeline from **validated text only** (0..N CandidateSignals, one BU/AS classification each); structured outputs with backend validation; Fake provider in CI / OpenAI opt-in smoke; fail-closed pipeline errors.

Named versions in use: schema `ai_observation_pipeline_v6`, prompt `ai_observation_pipeline_v6_2` (also on `AIUsageLog`).

Out: AI onboarding; direct DB mutation; AI-created Actions; AI permissions or urgency; Chat or image analysis; BYOK; prompt-routing UI; user-visible confidence as authority; fine-tuning on customer content; long-term raw prompt/output storage.

## 3. Invariants

AI proposes; backend validates. No images, audio files, or Chat content in the Observation pipeline. Every business-affecting call uses a strict schema; schema-valid ≠ business-valid. Logs must not contain clear-text prompts or raw model content. Failures must not corrupt business state. Providers remain replaceable (`FakeObservationPipelineProvider` vs OpenAI).

## 4. Objects (product concepts)

`AIProvider`, `AIRequest`, `AIUsageLog` (technical metadata), `AITranscript` (editable, not a standalone business object), `AIObservationPipelineResult`, `PromptVersion`, `AIError`. These names are not required ORM models.

Pipeline statuses live on `ObservationProcessing` (`queued`, `processing`, `processed`, `retrying`, `failed`).

## 5. Permissions / HTTP

RBAC and establishment scope before any AI call. Minimum context only. Users see simplified progress, not raw provider errors.

[`apps/api/schema.yml`](../../../apps/api/schema.yml): `POST …/transcriptions/`. Observation pipeline: submit Observation → Celery → Signals. Side effects: `houston/realtime/broadcast.py`, `houston/notifications/scheduling.py`.

## 6. Frontend / agent notes

Transcription must remain editable; failure → retry or type. Do not present confidence as authority. Do not reintroduce AI onboarding.

Inspect [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md) before changing I/O or segmentation. Eval command still used: `evaluate_observation_pipeline_v6`.
