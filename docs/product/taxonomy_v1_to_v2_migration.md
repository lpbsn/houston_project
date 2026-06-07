# Taxonomy v1 → v2 Migration

Status: authoritative  
Last reviewed: 2026-06-07  
Implementation status: **COMPLETE** (Lot 6 closed)

## Completion outcome

The taxonomy migration from legacy **Module → Domain → Subject** to **BusinessUnit → ActivitySubject** is complete.

- Lot 1: v2 model introduction and migration map — completed.
- Lot 2: RBAC scope migration to BusinessUnit-only — completed.
- Lot 3A: Signal v3 classification FKs and backfill — completed.
- Lot 3B: Observation pipeline v3 schema alignment — completed.
- Lot 4: Manual onboarding V2 as runtime source of truth — completed.
- Lot 6: legacy model/FK cleanup and compat removal — completed.

## Current authoritative model (post-Lot 6)

| Concern | v2 authoritative truth |
| --- | --- |
| Hierarchy | `BusinessUnit` → `ActivitySubject` |
| RBAC scope | `MembershipScope(scope_type=business_unit)` only |
| Signal classification | `affected_business_unit` + `responsible_business_unit` + `activity_subject` |
| Action classification | BU/AS contract; no product use of legacy taxonomy keys |
| Onboarding/runtime taxonomy | Manual onboarding V2, BU/AS only |

## Legacy compatibility status

No legacy compatibility is retained.

Removed/retired from active product model:

- `OperationalModule`, `OperationalDomain`, `OperationalSubject`
- `OnboardingCatalogModule`, `OnboardingCatalogDomain`, `OnboardingCatalogSubject`
- Signal legacy FKs `operational_module`, `operational_domain`, `operational_subject`
- `MembershipScope` module/domain/subject scope semantics
- Legacy `membership_scope_covers_module/domain/subject` compatibility helpers
- Deprecated operational-taxonomy API surface

## Preserved object

- `OperationalUnit` remains as structured location context, orthogonal to BU/AS classification.

## Source of truth documents

- [`domains/business_unit_taxonomy_domain.md`](domains/business_unit_taxonomy_domain.md)
- [`domains/rbac_permissions_domain.md`](domains/rbac_permissions_domain.md)
- [`domains/signal_domain.md`](domains/signal_domain.md)
- [`domains/action_domain.md`](domains/action_domain.md)
