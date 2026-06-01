# AI Observation Pipeline Contract

Status: authoritative (contract)  
Last reviewed: 2026-05-29  
Implementation status: **not_started** — doc only; runtime code Phase 4

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

## Output boundary

The pipeline produces **0..N `CandidateSignal` proposals** per Observation.

Each `CandidateSignal` proposes **exactly one** primary categorization triplet referencing **runtime** keys for the establishment:

- `operational_module_key`
- `operational_domain_key`
- `operational_subject_key`
- optional `operational_unit_key` (location only; orthogonal to triplet)

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

## Phase gate

**Do not implement** pipeline services, Celery tasks, models, or tests until:

- Phase B/C runtime taxonomy (modules, domains, subjects) is live per [`operational_taxonomy_domain.md`](operational_taxonomy_domain.md)
- Phase A documentation is human-validated
- Signal model Phase 4 is explicitly opened

## Related documents

- [`observation_domain.md`](observation_domain.md)
- [`signal_domain.md`](signal_domain.md)
- [`operational_taxonomy_domain.md`](operational_taxonomy_domain.md)
- [`ai_domain.md`](ai_domain.md)
