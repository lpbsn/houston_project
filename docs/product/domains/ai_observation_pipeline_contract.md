# AI Observation Pipeline Contract

Status: authoritative (contract)  
Last reviewed: 2026-06-13  
Implementation status: **pipeline v4** — prompt/schema, catalogue descriptions, backend aggregation on `issue_focus`, golden corpus G01–G11 green

## Purpose

Defines the structured AI output contract between a **persisted Observation** and backend-validated **CandidateSignals**, before any Signal is created or aggregated.

Target taxonomy: **BusinessUnit → ActivitySubject** ([`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)). Legacy Module/Domain/Subject routing is **removed** (Lot 6).

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
- `active_signals_context` (0..20 active Signals with BU/AS keys and `issue_focus`)
- `observation_id`, `establishment_id`, `submitted_at`, `media_count`, `schema_version`, `prompt_version`
- Optional `checklist_context` when `Observation.origin = checklist_task` (server-validated): `origin`, `checklist_execution_id`, `checklist_task_execution_id`, `template_title`, `task`, `business_unit_key` (nullable)

Each `business_unit` entry: `key`, `label`, `unit_type` (`dedicated` | `transversal`), `description`, `activity_subjects[]` (`key` = `normalized_name`, `label`, `description`).

Each `active_signals_context[]` entry: `signal_id`, `status`, `title`, `structured_summary`, `affected_business_unit_key`, `responsible_business_unit_key`, `activity_subject_key`, optional `operational_unit_key`, optional `location_text`, **`issue_focus`** (normalized persisted value — required for LLM create vs aggregate decisions).

**Catalogue seed (Lot 2)** : les descriptions de périmètre pour ~30 sujets prioritaires (stock, propreté, ménage, plomberie/eau, équipements, sécurité, BU transversales) vivent dans `docs/catalogue/*.csv`, sont importées via `make import-catalog`, et alimentent le runtime à l’onboarding. Le snapshot LLM expose uniquement les descriptions **runtime** actives.

### System prompt

- **Language**: French.
- **`prompt_version`**: `ai_observation_pipeline_v4`
- **`schema_version`**: `ai_observation_pipeline_v4`
- **MÉTHODE** : analyse problème par problème (grille symptôme / nature / action / lieu / responsable).
- **`issue_focus`** : focus opérationnel stable (objet, produit, équipement, situation ; lieu si discriminant).
- **DÉSAMBIGUÏSATION** : contexte grammatical (salissure vs fuite ; objet cassé vs équipement HS).
- **SEGMENTATION** : produits/objets différents → candidats différents même `activity_subject`.
- **AGRÉGATION** : hint `aggregate_into_signal_id` seulement si même `issue_focus` ; anti-biais `active_signals_context`.
- Routing rules (héritées du prompt pré-v4): separate **place** from **problem nature**; transversal priority; dedicated fallback.

## Output boundary

0..N candidates per Observation. Each candidate proposes **one** v4 classification:

- `issue_focus` — stable operational focus (1–80 chars); aggregation discriminant (persisted on Signal)
- `affected_business_unit_key` — pole impacted
- `responsible_business_unit_key` — pole treating the issue
- `activity_subject_key` — `normalized_name` under `responsible_business_unit`
- optional `operational_unit_key`, `location_text` (max 120, display only — **not** in aggregation key), `aggregate_into_signal_id`

`candidates: []` → backend outcome `no_signal_created`.

Rejected shapes: legacy `operational_*_key`, `detected_domains[]`, confidence scores, urgency.

## Backend validation (mandatory)

1. Keys exist in establishment runtime (active BU/AS).
2. `activity_subject.business_unit == responsible_business_unit`.
3. If `affected != responsible`, `responsible.unit_type == transversal`.
4. **No silent subject correction** — reject if subject ∉ responsible, except explicit fallback: `responsible = affected` when subject ∈ affected.
5. `location_text` resolved backend-side (unit label wins; clear if equals raw observation text).
6. Aggregation matches `(affected_bu, responsible_bu, activity_subject, operational_unit, normalize(issue_focus))`.
7. `aggregate_into_signal_id` hint is honored only when taxonomy matches **and** `normalize(issue_focus)` matches the target active Signal; otherwise a new Signal is created (`hint_rejected_reason=hint_issue_focus_mismatch` in audit log).

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
| `AI_OBSERVATION_PIPELINE_SCHEMA_VERSION` | `ai_observation_pipeline_v4` |
| `AI_OBSERVATION_PIPELINE_PROMPT_VERSION` | `ai_observation_pipeline_v4` |
| `AI_ISSUE_FOCUS_MAX_LENGTH` | `80` |

## Golden corpus

Apply-side truth without LLM: [`apps/api/houston/testing/pipeline_golden_v4_corpus.json`](../../../apps/api/houston/testing/pipeline_golden_v4_corpus.json) (cases **G01–G11**).

Tests: `houston/signals/tests/test_pipeline_v4_golden.py`

### G01–G08 — core v4 behaviors

| Case | Behavior |
| --- | --- |
| G01 | Segmentation: two distinct products → two Signals despite identical taxonomy quadruplet |
| G02, G08 | Anti-aggregation cross-product (mojito vs pain on same bar/stock quadruplet) |
| G03–G06 | Routing / disambiguation (housekeeping vs plumbing, cleanliness vs elevator failure) |
| G07 | Legitimate aggregation (same normalized `issue_focus`) |

### G09–G11 — semantic stability corpus

Frozen exact-match behavior: `normalize(issue_focus)` must match for aggregation. No aliases or fuzzy match in v4.

| Case | Active focus | Candidate focus | Expected |
| --- | --- | --- | --- |
| G09 | `sirop mojito` | `mojito syrup` | New Signal (no aggregate) |
| G10 | `pain` | `pain blanc` | New Signal (no aggregate) |
| G11 | `clim chambre 104` | `climatisation chambre 104` | New Signal (no aggregate) |

Lot 5 evaluation procedure: [`issue_focus_aggregation_eval_lot5.md`](../../engineering/issue_focus_aggregation_eval_lot5.md).

## Related documents

- [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md)
- [`taxonomy_v1_to_v2_migration.md`](../taxonomy_v1_to_v2_migration.md)
- [`observation_domain.md`](observation_domain.md)
- [`signal_domain.md`](signal_domain.md)
- [`ai_domain.md`](ai_domain.md)
