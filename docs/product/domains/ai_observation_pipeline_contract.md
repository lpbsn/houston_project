# AI Observation Pipeline Contract

Status: authoritative (contract)  
Last reviewed: 2026-06-02  
Implementation status: **in_progress** — runtime pipeline Phase 4+ (`houston.ai.observation_pipeline`, `houston.signals.services`)

## Purpose

Defines the structured AI output contract between a **persisted Observation** and backend-validated **CandidateSignals**, before any Signal is created or aggregated.

This contract is separate from:

- [`ai_domain.md`](ai_domain.md) — general AI boundary, logging, provider abstraction
- AI onboarding (`ai_onboarding_v3`, modules-only) — [`runtime_config_onboarding_domain.md`](runtime_config_onboarding_domain.md)
- Signal lifecycle — [`signal_domain.md`](signal_domain.md)

## Input boundary

| Allowed | Forbidden |
| --- | --- |
| Validated Observation **text** (typed or post-transcription) | Raw audio files |
| Establishment-scoped runtime taxonomy keys already activated | Image bytes or URLs to AI |
| Safe technical correlation metadata | Chat content |
| | Raw Observation text in logs beyond technical minimization rules |

Images linked to the Observation are **not** sent to AI in MVP.

### User payload (backend → provider)

The user message is **JSON only** (no duplicated system mission). Typical keys:

- `validated_text`, `taxonomy` (modules, domains, subjects, units snapshot)
- `active_signals_context` (0..20 active Signals: id, title, structured_summary, operational keys, status)
- technical metadata: `observation_id`, `establishment_id`, `submitted_at`, `media_count`, `schema_version`, `prompt_version`

### System prompt

- **Language**: French (field operations teams).
- **`prompt_version`**: `ai_observation_pipeline_v2` (tracked in `AIUsageLog`; distinct from response `schema_version`).
- **JSON field names**: English only (`title`, `structured_summary`, operational `*_key`, `aggregate_into_signal_id`).
- **`title`**: AI guidance ≤ 80 characters; backend may accept up to `SIGNAL_TITLE_MAX_LENGTH` (200) after validation.
- **Out of scope in prompt and schema**: urgency, priority, sentiment, keywords, suggested corrective action, incident/idea type, `detected_domains[]`, confidence scores, free-text categories, verbatim Observation copy.

## Output boundary

The pipeline produces **0..N `CandidateSignal` proposals** per Observation.

Each `CandidateSignal` proposes **exactly one** primary categorization triplet referencing **runtime** keys for the establishment:

- `operational_module_key`
- `operational_domain_key`
- `operational_subject_key`
- optional `operational_unit_key` — structured unit key from the taxonomy snapshot when a known catalogue unit applies (orthogonal to triplet)
- optional `location_text` — short free-text display location proposed by AI (e.g. entrance, bar, room 104); max 120 characters at pipeline boundary; must never be the full Observation text

Legacy shapes are **rejected**:

- `detected_domains[]` with confidence scores on one candidate
- multiple domain/subject pairs on a single candidate
- catalogue keys not present in the establishment runtime

## Segmentation rule (multi-problem Observations)

When the Observation text describes **distinct operational problems**, the pipeline must emit **multiple CandidateSignals** — one triplet per distinct problem.

Backend validation then creates **multiple Signals** (or aggregates each candidate separately). Never merge distinct problems into one Signal categorization.

Example (conceptual):

| Observation text (internal) | CandidateSignals |
| --- | --- |
| "Chambre 204 sale + clim HS lobby" | 1) subject proprete chambre + unit 204 ; 2) subject maintenance + domain/unit lobby |

## Aggregation proposal

Each `CandidateSignal` may include an optional `aggregate_into_signal_id` hint.

Backend decides whether to:

- create a new Signal, or
- aggregate into an **active** existing Signal with matching categorization

Aggregation must **not** target `resolved`, `canceled`, or `archived` Signals.

Only Signals listed in `active_signals_context` (active statuses) are valid aggregation targets for `aggregate_into_signal_id`.

Backend aggregation today also matches by operational triplet (+ optional unit); `aggregate_into_signal_id` is stored as `ai_aggregate_hint_signal_id` on `CandidateSignal` for audit.

## Structured output shape (candidate)

```json
{
  "schema_version": "ai_observation_pipeline_v1",
  "candidates": [
    {
      "title": "string",
      "structured_summary": "string",
      "operational_module_key": "hotel",
      "operational_domain_key": "hotel__hebergement",
      "operational_subject_key": "hotel__hebergement__proprete_des_chambres",
      "operational_unit_key": "rooms",
      "location_text": "chambre 312",
      "aggregate_into_signal_id": null
    }
  ]
}
```

Exact field names and Pydantic models are implementation details for Phase 4. Business validation remains mandatory after schema validation.

## Backend validation (mandatory)

Before persistence, backend must verify for each candidate:

1. Keys exist in establishment runtime (`OperationalModule`, `OperationalDomain`, `OperationalSubject`, optional `OperationalUnit`).
2. Domain belongs to module; subject belongs to domain (hierarchy).
3. Unit belongs to establishment if present.
4. No raw Observation text is copied into feed-safe fields beyond allowed structured summary rules.
5. Aggregation target, if any, is active and scope-compatible.
6. `location_text` on persisted `Signal` is resolved backend-side: when a validated `OperationalUnit` is set, `Signal.location_text` uses the unit catalogue **label**; otherwise normalized AI `location_text` is used unless it exactly matches Observation raw text (then cleared).

AI never writes Signals directly.

## Outcomes

| Outcome | Meaning |
| --- | --- |
| `signals_created` | One or more new Signals persisted |
| `signal_aggregated` | One or more candidates merged into active Signals |
| `no_signal_created` | Valid Observation; nothing actionable after validation |
| `not_actionable` | Observation persisted; pipeline declined to propose candidates |

## Failure and retry

- Pipeline failure does **not** delete the Observation.
- Retries are backend-controlled; user sees simplified status only.
- Standard logs store technical metadata only (`AIUsageLog` pattern); no prompts or raw model content in normal logs.

## Versioning

| Constant | Current value | Role |
| --- | --- | --- |
| `AI_OBSERVATION_PIPELINE_SCHEMA_VERSION` | `ai_observation_pipeline_v1` | Pydantic + OpenAI strict JSON schema |
| `AI_OBSERVATION_PIPELINE_PROMPT_VERSION` | `ai_observation_pipeline_v2` | System prompt revision (`AIUsageLog.prompt_version`) |

Bump `prompt_version` when changing system instructions without changing the response JSON shape.

## Related documents

- [`observation_domain.md`](observation_domain.md)
- [`signal_domain.md`](signal_domain.md)
- [`operational_taxonomy_domain.md`](operational_taxonomy_domain.md)
- [`ai_domain.md`](ai_domain.md)
