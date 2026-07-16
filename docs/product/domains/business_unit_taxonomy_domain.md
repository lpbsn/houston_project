# Business Unit Taxonomy Domain

Status: authoritative  
Last reviewed: 2026-07-16
Implementation status: **implemented** (BusinessUnit / ActivitySubject authoritative; Module/Domain/Subject v1 removed). Identity contracted: required `specific_name` / `normalized_specific_name` / `routing_key` + catalog FK (`PROTECT`); legacy instance columns `key` / `label` / `description` / `unit_type` removed.

> **Legacy model:** Module → Domain → Subject is obsolete and removed from active product contracts.

## Purpose

Defines Houston's operational categorization for onboarding, Signal routing, RBAC scopes, feed visibility, and the AI observation pipeline.

## Hierarchy

```
Establishment
  → BusinessUnit (concrete instance of a catalog generic)
    → ActivitySubject (generic association or free subject)
OperationalUnit (orthogonal) → structured physical location (e.g. Chambre 104)
location_text (on Signal) → free-text location context (e.g. "terrasse")
```

## Glossary

| Term | Definition |
| --- | --- |
| **CatalogBusinessUnit** | Global generic pole (`key`, `label`, `description`, `unit_type`, `active`). Seeded from CSV; not establishment truth. |
| **CatalogActivitySubject** | Global generic subject under one catalog BU (`key` max 150; must not start with `custom--`). |
| **BusinessUnit (instance)** | Establishment-scoped concrete pole. Display name is **`specific_name`**. Linked to a catalog generic via FK. |
| **`routing_key` (BU)** | Internal immutable identity: `{catalog_key}--{specific_slug≤48}--{id.hex[:16]}`. Generated once; never exposed on public API; used by IA snapshot/resolver and internal logs. |
| **`instance_description`** | Optional local description of the concrete BU instance. |
| **ActivitySubject** | Operational subject under exactly one BusinessUnit. Either a **generic association** (catalog FK) or a **free** subject (`custom--…` routing key). |
| **`normalized_name` / `normalized_specific_name`** | Slugs for uniqueness (`slugify_label`). AS unique per BU; BU `normalized_specific_name` unique per establishment (active and inactive). |
| **`unit_type`** | `dedicated` or `transversal` on **`CatalogBusinessUnit.unit_type` only**. Runtime reads it via the catalog link — not a user-editable instance field for new identity paths. |
| **Catalogue** | Global seed/autocomplete source. Import policy: [`docs/catalogue/README.md`](../../catalogue/README.md). |
| **affected / responsible BusinessUnit** | Signal FKs: pole impacted vs pole treating the issue. |
| **OperationalUnit** | Structured location layer; orthogonal to BusinessUnit. |

### Multi-instance example

Two dedicated instances of catalog `restaurant` in the same establishment:

| `specific_name` | Example `routing_key` |
| --- | --- |
| Food Court | `restaurant--food-court--550e8400e29b41d4` |
| Rooftop | `restaurant--rooftop--71c981d64e824f13` |

## Core invariants

### Catalogue / generics

- Every new BusinessUnit references a `CatalogBusinessUnit` (FK).
- `CatalogBusinessUnit.unit_type` is authoritative for dedicated vs transversal.
- Catalogue keys are append-only; absent keys on import are a **no-op** (see catalogue README).
- `CatalogActivitySubject.key` must not use the reserved `custom--` prefix.

### BusinessUnit instances

- `specific_name` is the sole public display name for the instance.
- `routing_key` is generated once (`build_business_unit_routing_key`), immutable on rename, unique per establishment, **never** in public API responses.
- Dedicated: multiple active instances of the same catalog generic are allowed.
- Transversal: **at most one active instance per transversal catalog generic** per establishment (`duplicate_transversal_catalog_instance`).
- Creation never implicitly reactivates an inactive instance; reactivation is an explicit service/endpoint.
- Deactivation refused while active membership scopes exist (`business_unit_has_membership_scopes`).
- No automatic membership-scope extension when a new instance is created.
- No BusinessUnit named « Non attribué ».

### ActivitySubject

- Generic association: `catalog_activity_subject` set; `routing_key = catalog.key`; `source = catalog_suggestion`; local `label`/`description` empty (display via catalogue).
- Free subject: no catalog FK; local `label` required; `routing_key = custom--{slug}--{uuidhex}`; `source = manual`.
- Catalog subject must belong to the same catalog BU as the instance (`catalog_subject_business_unit_mismatch`).
- Uniqueness `(business_unit, normalized_name)` and `(business_unit, routing_key)`; inactive rows still reserve names.
- New catalog subjects are **not** retroactively seeded onto existing instances.

### RBAC / feed

- RBAC scopes are **BusinessUnit UUID only** (`MembershipScope`) — never ActivitySubject, never catalog key, never `routing_key`.
- Feed filters use `business_unit_ids` (UUID). `business_unit_keys` is rejected.
- No `MembershipFeedSubscription` / ActivitySubject opt-out in this phase.
- `OperationalUnit` coexists with `location_text` on Signal.

## Services (create ≠ reactivate)

| Service | Behavior |
| --- | --- |
| `_create_business_unit_core` | Creates BU + `routing_key` only; no subject seed; never reactivates. |
| `create_runtime_business_unit` | Core + atomic seed of all **active** catalog subjects for the generic. |
| `create_onboarding_business_unit` | Core + materializes **exactly** the subjects from the onboarding payload (no completion). |
| `reactivate_business_unit` | Sets `active=True` by UUID; preserves UUID/`routing_key`/`specific_name`; no seed; no scope recreation. |
| `update_business_unit_specific_name` | Recalculates `normalized_specific_name`; keeps `routing_key` unchanged. |

Establishment lock: `Establishment.select_for_update()` on create / reactivate / rename paths.

## Public API (Lot 5)

Authoritative HTTP shapes: [`apps/api/schema.yml`](../../../apps/api/schema.yml).

BusinessUnit public payload (no `routing_key`, no instance `key`/`label`):

```json
{
  "id": "<uuid>",
  "specific_name": "Food Court",
  "instance_description": "Zone restauration niveau 0",
  "active": true,
  "generic": {
    "key": "restaurant",
    "label": "Restaurant",
    "description": "Pôle restauration",
    "unit_type": "dedicated"
  }
}
```

ActivitySubject public: generics expose `catalog_key`, effective `label`/`description`, `is_generic`; free subjects expose local `label`/`description`. No `routing_key`.

Runtime endpoints (under establishment): create BU, PATCH instance fields, `POST …/business-units/{id}/reactivate/`, create/reactivate activity subjects. See schema for paths.

## Signal classification

Each Signal carries:

- `affected_business_unit` (required)
- `responsible_business_unit` (required)
- `activity_subject` (required; must belong to `responsible_business_unit`)
- `operational_unit` (optional)
- `location_text` (optional)

**Rules:**

1. All FKs belong to the same establishment as the Signal.
2. `activity_subject.business_unit_id == responsible_business_unit_id`.
3. If `affected != responsible`, then responsible catalog `unit_type == transversal`.
4. If `affected == responsible`, `unit_type` may be dedicated or transversal.

## RBAC

| Role | Scope | Ma vue visibility | Actionability |
| --- | --- | --- | --- |
| Owner/Director | Global | All active signals | All |
| Manager | 1+ BusinessUnit UUID | affected OR responsible in scopes | responsible in scopes |
| Staff | 1+ BusinessUnit UUID | affected OR responsible in scopes | None |

## Contracted identity (current)

| Model | Required identity | Notes |
| --- | --- | --- |
| BusinessUnit | `specific_name`, `normalized_specific_name`, `routing_key`, `instance_description`, `catalog_business_unit` (`PROTECT`) | Legacy instance columns `key` / `label` / `description` / `unit_type` **removed** |
| ActivitySubject | `routing_key` required; generics: catalog FK (`PROTECT`) + empty local `label`/`description`; free: no catalog FK + local `label` + `custom--…` routing_key | CheckConstraint `activity_subject_generic_or_free_ck` |

`routing_key` is internal only — never in public OpenAPI. Public Signal/Obs/AP summaries may still expose compatibility fields `*_business_unit_key` / `*_label` sourced from `normalized_specific_name` / `specific_name` — **never identifiers** (UUID filters/RBAC remain authoritative).

Onboarding: **`onboarding_proposal_v4` only** at runtime. Non-terminal v3 rows are converted or `REJECTED` (`unsupported_schema_version_v3`) via migration/`make preflight-onboarding-v3`; terminal v3 payloads kept as history.

Deploy / reset order for environments: [`prod_test_runbook.md`](../../deploy/prod_test_runbook.md) §7b.

## Catalogue source

Seed/runtime split and import policy: [`docs/catalogue/README.md`](../../catalogue/README.md).

| Layer | Location | Role |
| --- | --- | --- |
| Raw export | [`docs/catalogue/suggestion_source.csv`](../../catalogue/suggestion_source.csv) | Trace of the business Excel export |
| Normalized seed | [`docs/catalogue/business_units.csv`](../../catalogue/business_units.csv), [`docs/catalogue/activity_subjects.csv`](../../catalogue/activity_subjects.csv) | Versioned git seed |
| Runtime DB | `CatalogBusinessUnit`, `CatalogActivitySubject` | Autocomplete + FK targets for onboarding/runtime |

**Local setup after migrate:** `make import-catalog` (then `make catalog-check`). Do not run host-native `uv run` under `apps/api` for day-to-day ops — use Make / Docker targets.

Optional management flags: `--dry-run`, `--strict`, `--regenerate-from-source`.

**Runtime rules:**

- Autocomplete reads PostgreSQL catalogue models only — not CSV files.
- Without import, autocomplete is empty (no fallback).
- Catalogue is a completion aid and FK source; establishment instances are business truth.
- New instances require a catalog generic; free activity subjects remain establishment-local without a catalog AS row.

## Related contracts

- Catalogue import: [`docs/catalogue/README.md`](../../catalogue/README.md)
- Onboarding: [`runtime_config_onboarding_domain.md`](runtime_config_onboarding_domain.md)
- RBAC: [`rbac_permissions_domain.md`](rbac_permissions_domain.md)
- Signal: [`signal_domain.md`](signal_domain.md)
- Observation pipeline: [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)
- Local reset: [`docs/engineering/local_development.md`](../../engineering/local_development.md)
- Deploy / contraction: [`docs/deploy/prod_test_runbook.md`](../../deploy/prod_test_runbook.md)
