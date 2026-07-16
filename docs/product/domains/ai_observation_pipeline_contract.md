# AI Observation Pipeline Contract

Status: authoritative (contract)  
Last reviewed: 2026-07-16
Implementation status: **pipeline v5** — prompt/schema use `routing_key`; snapshot includes generic/instance descriptions; backend aggregation on `issue_focus`; golden corpus G01–G11 green

## Purpose

Defines the structured AI output contract between a **persisted Observation** and backend-validated **CandidateSignals**, before any Signal is created or aggregated.

Target taxonomy: **BusinessUnit → ActivitySubject** ([`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)). Legacy Module/Domain/Subject routing is **removed** (Lot 6). Resolution is by **`routing_key`**, never by public API fields alone.

## Input boundary

| Allowed | Forbidden |
| --- | --- |
| Validated Observation **text** | Raw audio, images |
| Establishment **runtime** snapshot of active, snapshot-ready `BusinessUnit` + `ActivitySubject` | Global catalogue (`CatalogBusinessUnit`, CSV) as routing truth |
| Generic + instance descriptions from runtime/catalog link | Invented keys or catalogue-only keys not present on the instance |
| Safe technical metadata | Raw Observation text in logs |
| Internal `routing_key` values in the LLM payload | Exposing `routing_key` on public REST responses |

### User payload (backend → provider)

JSON only. Keys:

- `validated_text`, `establishment_taxonomy` (`business_units[]`, `operational_units[]`)
- `active_signals_context` (0..20 active Signals with BU/AS **routing_key** fields and `issue_focus`)
- `observation_id`, `establishment_id`, `submitted_at`, `media_count`, `schema_version`, `prompt_version`
- Optional checklist-style context when origin requires it (server-validated): may include `business_unit_routing_key` (nullable)

Each snapshot-ready `business_unit` entry (active only, with identity + catalog link):

- `routing_key`, `specific_name`
- `generic_label`, `generic_description` (from `CatalogBusinessUnit`)
- `instance_description` (from BusinessUnit)
- `unit_type` (from `CatalogBusinessUnit.unit_type`)
- `activity_subjects[]`: `routing_key`, `label`, `description`, `source` (`catalog` | `free`) — active subjects with routing_key only

Each `active_signals_context[]` entry: `signal_id`, `status`, `title`, `structured_summary`, `affected_business_unit_routing_key`, `responsible_business_unit_routing_key`, `activity_subject_routing_key`, optional `operational_unit_key`, optional `location_text`, **`issue_focus`**.

**Catalogue seed:** perimeter descriptions live in `docs/catalogue/*.csv`, imported via `make import-catalog`, and feed runtime at onboarding/runtime create. The LLM snapshot exposes only **runtime** active rows (see [`docs/catalogue/README.md`](../../catalogue/README.md)).

### System prompt

- **Language**: French.
- **`prompt_version`**: `ai_observation_pipeline_v5`
- **`schema_version`**: `ai_observation_pipeline_v5`
- **MÉTHODE** : analyse problème par problème (grille symptôme / nature / action / lieu / responsable).
- **`issue_focus`** : focus opérationnel stable (objet, produit, équipement, situation ; lieu si discriminant).
- **DÉSAMBIGUÏSATION** : contexte grammatical (salissure vs fuite ; objet cassé vs équipement HS).
- **SEGMENTATION** : produits/objets différents → candidats différents même `activity_subject`.
- **AGRÉGATION** : hint `aggregate_into_signal_id` seulement si même `issue_focus` ; anti-biais `active_signals_context`.
- Routing: separate **place** from **problem nature**; transversal priority; dedicated fallback; every `routing_key` must exist in the snapshot.

## Output boundary

0..N candidates per Observation. Each candidate proposes **one** v5 classification:

- `issue_focus` — stable operational focus (1–80 chars); aggregation discriminant (persisted on Signal)
- `affected_business_unit_routing_key` — pole impacted
- `responsible_business_unit_routing_key` — pole treating the issue
- `activity_subject_routing_key` — subject under **responsible** BusinessUnit
- optional `operational_unit_key`, `location_text` (max 120, context only — **not** in aggregation key), `aggregate_into_signal_id`

`candidates: []` → backend outcome `no_signal_created`.

Rejected shapes: legacy `operational_*_key` taxonomy, `*_business_unit_key` / `activity_subject_key` as primary routing fields, `detected_domains[]`, confidence scores, urgency.

## Backend validation (mandatory)

1. Resolve active BU by `(establishment_id, routing_key)` for affected and responsible.
2. Resolve active ActivitySubject by `(business_unit=responsible, routing_key)` — **never** resolve a subject without the responsible BU filter.
3. If `affected != responsible`, responsible catalog `unit_type == transversal`.
4. **No silent subject correction** — reject if subject ∉ responsible, except explicit fallback: `responsible = affected` when subject ∈ affected.
5. `location_text` resolved backend-side (unit label wins; clear if equals raw observation text).
6. Aggregation matches `(affected_bu, responsible_bu, activity_subject, operational_unit, normalize(issue_focus))`.
7. `aggregate_into_signal_id` hint is honored only when taxonomy matches **and** `normalize(issue_focus)` matches the target active Signal; otherwise a new Signal is created (`hint_rejected_reason=hint_issue_focus_mismatch` in audit log).

Inactive BU/AS or sibling-BU subjects are rejected. Distinct instance `routing_key` values (e.g. Food Court vs Rooftop) must resolve to distinct BusinessUnits.

## Outcomes

| Outcome | Meaning |
| --- | --- |
| `signals_created` | One or more new Signals |
| `signal_aggregated` | Merged into active Signals |
| `no_signal_created` | No Signal produced: `candidates: []`, validation rejection, or no actionable candidate after validation (includes cases where the pipeline would not propose a Signal) |

**MVP:** no separate `not_actionable` outcome — use `no_signal_created` only. A distinct « AI declined » analytics outcome requires an explicit future product decision.

## Versioning

| Constant | Value |
| --- | --- |
| `AI_OBSERVATION_PIPELINE_SCHEMA_VERSION` | `ai_observation_pipeline_v5` |
| `AI_OBSERVATION_PIPELINE_PROMPT_VERSION` | `ai_observation_pipeline_v5` |
| `AI_ISSUE_FOCUS_MAX_LENGTH` | `80` |

## Golden corpus

Apply-side truth without LLM: [`apps/api/houston/testing/pipeline_golden_v4_corpus.json`](../../../apps/api/houston/testing/pipeline_golden_v4_corpus.json) (cases **G01–G11** — corpus file name retained; pipeline schema/prompt are v5).

Tests: `houston/signals/tests/test_pipeline_v4_golden.py`

### G01–G08 — core behaviors

| Case | Behavior |
| --- | --- |
| G01 | Segmentation: two distinct products → two Signals despite identical taxonomy quadruplet |
| G02, G08 | Anti-aggregation cross-product (mojito vs pain on same bar/stock quadruplet) |
| G03–G06 | Routing / disambiguation (housekeeping vs plumbing, cleanliness vs elevator failure) |
| G07 | Legitimate aggregation (same normalized `issue_focus`) |

### G09–G11 — semantic stability corpus

Frozen exact-match behavior: `normalize(issue_focus)` must match for aggregation. No aliases or fuzzy match.

| Case | Active focus | Candidate focus | Expected |
| --- | --- | --- | --- |
| G09 | `sirop mojito` | `mojito syrup` | New Signal (no aggregate) |
| G10 | `pain` | `pain blanc` | New Signal (no aggregate) |
| G11 | `clim chambre 104` | `climatisation chambre 104` | New Signal (no aggregate) |

Lot 5 evaluation: `python manage.py report_issue_focus_aggregation_eval` via Docker/Make — see [`engineering/testing.md`](../../engineering/testing.md).

## Related documents

- [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)
- [`observation_domain.md`](observation_domain.md)
- [`signal_domain.md`](signal_domain.md)
- [`ai_domain.md`](ai_domain.md)
