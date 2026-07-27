# AI Observation Pipeline Contract

Status: authoritative (contract)  
Last reviewed: 2026-07-25
Implementation status: **pipeline v6** — schema `ai_observation_pipeline_v6` ; prompt `ai_observation_pipeline_v6_2` ; dual context (`establishment_context` + `routing_taxonomy`) ; nullable routing keys ; `signal_kind` actionable|informational ; author scope is server-only (not sent to the LLM) ; backend aggregation on normalized `issue_focus` (no LLM aggregate hint)

## Purpose

Defines the structured AI output contract between a **persisted Observation** and backend-validated **CandidateSignals**, before any Signal is created or aggregated.

Target taxonomy: **BusinessUnit → ActivitySubject** ([`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)). Legacy Module/Domain/Subject routing is **removed**. Resolution is by **`routing_key`**, never by public API fields alone.

## Input boundary

| Allowed | Forbidden |
| --- | --- |
| Validated Observation **text** | Raw audio, images |
| `establishment_context` (all active BUs, including non-routable) | Global catalogue as routing truth |
| `routing_taxonomy` (routable BUs/AS/OU only) | Invented keys outside `routing_taxonomy` |
| Optional `action_plan_context` when linked | Author membership / scope keys ; nominative author identity |
| Safe technical metadata | `active_signals_context` / LLM aggregate hints |
| Internal `routing_key` values in the LLM payload | Exposing `routing_key` on public REST responses |
|  | Raw Observation text in logs |

### User payload (backend → provider)

JSON only. Keys:

- `validated_text`, `establishment_context`, `routing_taxonomy`
- `observation_id`, `establishment_id`, `submitted_at`, `media_count`, `schema_version`, `prompt_version`
- Optional `action_plan_context` when the Observation is linked to an action-plan execution/task

Author membership scope is **not** sent to the LLM. When the candidate remains totally unclassified after resolve + responsible text-anchoring, the backend may set `affected_business_unit` from a unique author pole (`author_scope_fallback`).

`establishment_context.active_business_units` is structural context only. Runtime routing keys must come from `routing_taxonomy`.

**Catalogue seed:** perimeter descriptions live in `docs/catalogue/*.csv`, imported via `make import-catalog`, and feed runtime at onboarding/runtime create. The LLM payload exposes runtime rows only (see [`docs/catalogue/README.md`](../../catalogue/README.md)).

### System prompt

- **Language**: French.
- **`prompt_version`**: `ai_observation_pipeline_v6_2`
- **`schema_version`**: `ai_observation_pipeline_v6`
- **MÉTHODE** : analyse **fait par fait** (anomalies **ou** informations opérationnelles).
- **0 / 1 / N** : émettre un candidat par fait opérationnel ; `[]` seulement pour politesse, fausse alerte sans fait résiduel, ou absence de fait.
- **`signal_kind`** : `actionable` (intervention attendue) ou `informational` (à connaître / diffuser / surveiller).
- **Informational fields** : `canonical_object` = objet/thème ; `issue_focus` = état, disponibilité ou changement annoncé (court, stable).
- **Anti-sur-segmentation** : invitation / modalité d’accès liée à l’info principale ≠ candidat séparé ni anomalie (ex. « Les plannings sont disponibles, venez les demander » → exactement 1 informational).
- **`issue_focus`** : discriminant d’agrégation backend (1–80 chars).
- **DÉSAMBIGUÏSATION** : contexte grammatical (salissure vs fuite ; objet cassé vs équipement HS).
- **SEGMENTATION** : produits/objets/faits indépendants → candidats différents.
- **AGRÉGATION** : backend only after resolve ; no `aggregate_into_signal_id` in the LLM contract.
- Routing: separate **place** from **fact nature**; transversal priority; dedicated fallback; every `routing_key` must exist in `routing_taxonomy` (else null → unassigned).

## Output boundary

0..N candidates per Observation (max 5). Each candidate proposes one classification:

- `title`, `structured_summary`
- `issue_focus` — stable operational focus (1–80 chars); aggregation discriminant (persisted on Signal)
- `canonical_object` — object/theme (persisted on CandidateSignal)
- `signal_kind` — `actionable` | `informational`
- `expected_action` — closed enum or null (`inform` / `monitor` preferred for informational)
- `information_type` — null if actionable ; non-empty free string (max 64) if informational
- `affected_business_unit_routing_key`, `responsible_business_unit_routing_key`, `activity_subject_routing_key` — nullable
- optional `operational_unit_key`, `location_text` (max 120, context only — **not** in aggregation key)

`candidates: []` → backend outcome `no_signal_created`.

Rejected shapes: legacy `operational_*_key` taxonomy, `*_business_unit_key` / `activity_subject_key` as primary routing fields, `detected_domains[]`, confidence scores, urgency, `aggregate_into_signal_id`, `routing_status` (backend-only).

## Backend validation (mandatory)

1. Resolve active BU by `(establishment_id, routing_key)` for affected and responsible when keys are non-null.
2. Resolve active ActivitySubject by `(business_unit=responsible, routing_key)` — **never** resolve a subject without the responsible BU filter.
3. Partial / invalid keys → `routing_status=unassigned` ; candidate is still persisted and may create a Signal (no drop for missing subject alone).
4. If `affected != responsible`, responsible catalog `unit_type == transversal` (resolver correction rules apply).
5. `location_text` resolved backend-side (unit label wins; clear if equals raw observation text).
6. Aggregation matches `(affected_bu, responsible_bu, activity_subject, operational_unit, normalize(issue_focus))` for **resolved** candidates only.
7. Apply does **not** filter on `signal_kind` — informational candidates create Signals like actionable ones.

Inactive BU/AS or sibling-BU subjects are rejected or corrected per resolver rules. Distinct instance `routing_key` values (e.g. Food Court vs Rooftop) must resolve to distinct BusinessUnits.

## Outcomes

| Outcome | Meaning |
| --- | --- |
| `signals_created` | One or more new Signals |
| `signal_aggregated` | Merged into active Signals |
| `no_signal_created` | No Signal produced: `candidates: []`, validation rejection, or no applied candidate |

**MVP:** no separate `not_actionable` outcome — use `no_signal_created` only. Informational facts are first-class candidates, not an empty-list path.

## Versioning

| Constant | Value |
| --- | --- |
| `AI_OBSERVATION_PIPELINE_SCHEMA_VERSION` | `ai_observation_pipeline_v6` |
| `AI_OBSERVATION_PIPELINE_PROMPT_VERSION` | `ai_observation_pipeline_v6_2` |
| `AI_ISSUE_FOCUS_MAX_LENGTH` | `80` |
| `AI_INFORMATION_TYPE_MAX_LENGTH` | `64` |
| `MAX_CANDIDATES_PER_OBSERVATION` | `5` |

## Acceptance corpus

Functional expectations: [`apps/api/houston/testing/pipeline_v6_acceptance_corpus.json`](../../../apps/api/houston/testing/pipeline_v6_acceptance_corpus.json) (S15-01…S15-23 + S15-D1).

Informational / prompt v6.1 cases include S15-07, S15-13, S15-21…S15-23. Lot4b owns the prompt correctif + targeted live smoke ; Lot 10 owns full business smoke + docs cutover.

Apply-side golden (non-LLM): [`apps/api/houston/testing/pipeline_golden_v4_corpus.json`](../../../apps/api/houston/testing/pipeline_golden_v4_corpus.json) (G01–G11).

## Related documents

- [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)
- [`observation_domain.md`](observation_domain.md)
- [`signal_domain.md`](signal_domain.md)
- [`ai_domain.md`](ai_domain.md)
