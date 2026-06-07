# AI Observation Pipeline Contract

Status: authoritative (contract)  
Last reviewed: 2026-06-07  
Implementation status: **in_progress** — Lot 3B (`houston.ai.observation_pipeline`, `houston.signals.services`)

## Purpose

Defines the structured AI output contract between a **persisted Observation** and backend-validated **CandidateSignals**, before any Signal is created or aggregated.

Target taxonomy: **BusinessUnit → ActivitySubject** ([`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)). Legacy Module/Domain/Subject is **obsolete for product routing** (DB shim only until Lot 6).

## Input boundary

| Allowed | Forbidden |
| --- | --- |
| Validated Observation **text** | Raw audio, images |
| Establishment **runtime** `BusinessUnit` + `ActivitySubject` snapshot (active only) | Global catalogue (`CatalogBusinessUnit`, CSV) as routing truth |
| `BusinessUnit.description` and `ActivitySubject.description` from runtime DB | Invented keys or catalogue-only keys |
| Safe technical metadata | Raw Observation text in logs |

### User payload (backend → provider)

JSON only. Keys:

- `validated_text`, `establishment_taxonomy` (`business_units[]`, `operational_units[]`)
- `active_signals_context` (0..20 active Signals with BU/AS keys)
- `observation_id`, `establishment_id`, `submitted_at`, `media_count`, `schema_version`, `prompt_version`

Each `business_unit` entry: `key`, `label`, `unit_type` (`dedicated` | `transversal`), `description`, `activity_subjects[]` (`key` = `normalized_name`, `label`, `description`).

### System prompt

- **Language**: French.
- **`prompt_version`**: `ai_observation_pipeline_v3`
- **`schema_version`**: `ai_observation_pipeline_v3`
- Routing rules: separate **place** (`affected_business_unit`, `location_text`) from **problem nature** (`responsible_business_unit`, `activity_subject`).
- Transversal BU takes priority when problem matches their `activity_subject`.
- Fallback: `responsible = affected` only when no relevant transversal exists in snapshot.

## Output boundary

0..N candidates per Observation. Each candidate proposes **one** v3 classification:

- `affected_business_unit_key` — pole impacted
- `responsible_business_unit_key` — pole treating the issue
- `activity_subject_key` — `normalized_name` under `responsible_business_unit`
- optional `operational_unit_key`, `location_text` (max 120), `aggregate_into_signal_id`

`candidates: []` → backend outcome `no_signal_created`.

Rejected shapes: legacy `operational_*_key`, `detected_domains[]`, confidence scores, urgency.

## Backend validation (mandatory)

1. Keys exist in establishment runtime (active BU/AS).
2. `activity_subject.business_unit == responsible_business_unit`.
3. If `affected != responsible`, `responsible.unit_type == transversal`.
4. **No silent subject correction** — reject if subject ∉ responsible, except explicit fallback: `responsible = affected` when subject ∈ affected.
5. `location_text` resolved backend-side (unit label wins; clear if equals raw observation text).
6. Aggregation matches `(affected_bu, responsible_bu, activity_subject, operational_unit)` — not legacy triplet.

Legacy `operational_module/domain/subject` FKs on `Signal` are **DB shim only** until Lot 6 — not product truth.

## Outcomes

| Outcome | Meaning |
| --- | --- |
| `signals_created` | One or more new Signals |
| `signal_aggregated` | Merged into active Signals |
| `no_signal_created` | Nothing actionable after validation |
| `not_actionable` | Pipeline declined to propose |

## Versioning

| Constant | Value |
| --- | --- |
| `AI_OBSERVATION_PIPELINE_SCHEMA_VERSION` | `ai_observation_pipeline_v3` |
| `AI_OBSERVATION_PIPELINE_PROMPT_VERSION` | `ai_observation_pipeline_v3` |

## Related documents

- [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)
- [`taxonomy_v1_to_v2_migration.md`](../taxonomy_v1_to_v2_migration.md) — Lot 3B
- [`observation_domain.md`](observation_domain.md)
- [`signal_domain.md`](signal_domain.md)
- [`ai_domain.md`](ai_domain.md)
