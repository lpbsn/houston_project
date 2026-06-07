# Business Unit Taxonomy Domain

Status: authoritative (target model)  
Last reviewed: 2026-06-06  
Implementation status: **in progress** (refactor v2 — see [`taxonomy_v1_to_v2_migration.md`](../taxonomy_v1_to_v2_migration.md))

> **Legacy model:** Module → Domain → Subject is **obsolete**. See [`docs/archive/taxonomy_v1/operational_taxonomy_domain.md`](../../archive/taxonomy_v1/operational_taxonomy_domain.md).

## Purpose

Defines Houston's operational categorization for onboarding, Signal routing, RBAC scopes, and feed visibility.

## Hierarchy (target)

```
Establishment
  → BusinessUnit (pôle d'activité)
    → ActivitySubject (sujet opérationnel)
OperationalUnit (orthogonal) → structured physical location (e.g. Chambre 104)
location_text (on Signal) → free-text location context (e.g. "terrasse")
```

## Glossary

| Term | Definition |
| --- | --- |
| **BusinessUnit** | Establishment-scoped activity pole (Hotel, Restaurant, Maintenance, RH, …). Has `unit_type`: `dedicated` or `transversal`. |
| **ActivitySubject** | Operational subject attached to exactly one BusinessUnit (Propreté chambre, Climatisation, …). |
| **normalized_name** | Slug derived from label for uniqueness **within** a BusinessUnit (`UniqueConstraint(business_unit, normalized_name)`). Same subject label may exist on multiple BusinessUnits. |
| **unit_type** | `dedicated` = pole tied to a specific activity/space; `transversal` = pole that may act across other poles. Configurable per establishment; catalogue suggests defaults only. |
| **Catalogue** | Global suggestion source for autocomplete. **Not** establishment business truth. |
| **affected_business_unit** | Signal field: pole impacted by the issue. |
| **responsible_business_unit** | Signal field: pole responsible for treatment. |
| **OperationalUnit** | Structured location layer; **conserved**, orthogonal to BusinessUnit. |

## Core invariants

- Catalogue suggests; establishment configuration decides.
- Same label may be a BusinessUnit in one establishment and an ActivitySubject in another.
- RBAC scopes are **BusinessUnit-only** — never ActivitySubject.
- No `MembershipFeedSubscription` or ActivitySubject opt-out in this refactor.
- `OperationalUnit` is not deprecated; coexists with `location_text` on Signal.

## Signal classification (target)

Each Signal carries:

- `affected_business_unit` (required)
- `responsible_business_unit` (required)
- `activity_subject` (required; must belong to `responsible_business_unit`)
- `operational_unit` (optional; structured location)
- `location_text` (optional; free-text location)

**Rules:**

1. All FKs belong to the same establishment as the Signal.
2. `activity_subject.business_unit_id == responsible_business_unit_id`.
3. If `affected != responsible`, then `responsible.unit_type == transversal`.
4. If `affected == responsible`, `unit_type` may be dedicated or transversal.

## RBAC (target)

| Role | Scope | Ma vue visibility | Actionability |
| --- | --- | --- | --- |
| Owner/Director | Global | All active signals | All |
| Manager | 1+ BusinessUnit | affected OR responsible in scopes | responsible in scopes |
| Staff | 1+ BusinessUnit | affected OR responsible in scopes | None |

## Catalogue source

The v2 catalogue uses a **seed/runtime split**:

| Layer | Location | Role |
| --- | --- | --- |
| Raw export | [`docs/catalogue/suggestion_source.csv`](../../catalogue/suggestion_source.csv) | Trace of the business Excel export |
| Normalized seed | [`docs/catalogue/business_units.csv`](../../catalogue/business_units.csv), [`docs/catalogue/activity_subjects.csv`](../../catalogue/activity_subjects.csv) | Versioned git seed only |
| Runtime DB | `CatalogBusinessUnit`, `CatalogActivitySubject` | Autocomplete + future manual onboarding FK targets |

**Setup (required after migrate):**

```bash
cd apps/api
uv run python manage.py import_business_unit_catalog
```

Optional flags: `--dry-run`, `--strict`, `--regenerate-from-source` (rebuild normalized seed CSVs from `suggestion_source.csv`).

**Runtime rules:**

- Autocomplete endpoints read **PostgreSQL catalogue models only** — not CSV files.
- Without import, autocomplete returns an empty list (no fallback).
- The catalogue is a **completion aid**, never establishment business truth.
- Onboarding may create `BusinessUnit` / `ActivitySubject` rows without a catalogue match.
- `default_unit_type` on `CatalogBusinessUnit` is a **suggestion only**; establishment `BusinessUnit.unit_type` remains user-configurable.

Legacy v1 onboarding catalogue is seeded in `OnboardingCatalogModule` / `OnboardingCatalogDomain` / `OnboardingCatalogSubject` (migration `0007`). It is **not** used by v2 autocomplete.

## Related contracts

- Migration: [`taxonomy_v1_to_v2_migration.md`](../taxonomy_v1_to_v2_migration.md)
- Onboarding: [`runtime_config_onboarding_domain.md`](runtime_config_onboarding_domain.md)
- RBAC: [`rbac_permissions_domain.md`](rbac_permissions_domain.md)
- Signal: [`signal_domain.md`](signal_domain.md)
- Observation pipeline: [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)
