# Taxonomy v1 → v2 Migration

Status: authoritative  
Last reviewed: 2026-06-06  
Implementation status: **in progress**

## Summary

| | v1 (legacy, implemented) | v2 (target) |
| --- | --- | --- |
| Hierarchy | Module → Domain → Subject | BusinessUnit → ActivitySubject |
| RBAC scope | module / domain / subject | BusinessUnit only |
| Signal taxonomy | operational_module/domain/subject triplet | affected/responsible BU + activity_subject |
| Catalogue | OnboardingCatalogModule/Domain/Subject tree | CatalogBusinessUnit / CatalogActivitySubject suggestions |
| Onboarding | AI-driven proposal | Manual human-accompanied flow |

## Strategy: Expand → Backfill → Cutover → Contract

1. **Lot 1:** Create v2 models parallel to v1; `TaxonomyMigrationMap`; backfill command.
2. **Lot 2:** MembershipScope → single `business_unit` FK.
3. **Lot 3A:** Signal new FKs + backfill; keep v1 FKs until Lot 6.
4. **Lot 4:** Manual onboarding creates v2 truth for new establishments.
5. **Lot 3B:** Observation pipeline schema v3.
6. **Lot 6:** Drop v1 models and FKs.

## Backfill heuristics (default)

| Legacy | Default mapping | Notes |
| --- | --- | --- |
| `OperationalModule` | `BusinessUnit` (`dedicated`) | Transversal modules (Maintenance, RH) → `transversal` |
| `OperationalDomain` | `ActivitySubject` under module-as-BU | Manual review for ambiguous domains |
| `OperationalSubject` | `ActivitySubject` under parent domain's BU | Uses `normalized_name` from legacy key |

## Signal backfill (Lot 3A)

- `affected_business_unit` ← module/domain-derived BU
- `responsible_business_unit` ← same, unless transversal routing rule applies
- `activity_subject` ← migrated subject
- `operational_unit` ← unchanged if present

## Rollback guards

- Feature flags: `TAXONOMY_V2_READ`, `TAXONOMY_V2_WRITE`, `OBSERVATION_PIPELINE_V3`
- Do not drop v1 tables while any Signal lacks v2 FKs
- DB snapshot before production backfill

## Obsolete after Lot 6

- `OperationalModule`, `OperationalDomain`, `OperationalSubject`
- `OnboardingCatalogModule`, `OnboardingCatalogDomain`, `OnboardingCatalogSubject`
- Signal FKs `operational_module`, `operational_domain`, `operational_subject`
- `MembershipScope` module/domain/subject columns
- `GET .../operational-taxonomy/` (replaced by `business-units/`)

## Preserved

- `OperationalUnit` (structured location)
- AI onboarding endpoint until Lot 6 (deprecated, not 410)
