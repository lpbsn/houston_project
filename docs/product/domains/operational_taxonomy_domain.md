# Operational Taxonomy Domain

> **Status: OBSOLETE (v1)** — Superseded by [`business_unit_taxonomy_domain.md`](business_unit_taxonomy_domain.md). Archived copy: [`docs/archive/taxonomy_v1/operational_taxonomy_domain.md`](../../archive/taxonomy_v1/operational_taxonomy_domain.md).

Status: obsolete  
Last reviewed: 2026-05-29  
Implementation status: partial (legacy Module → Domain → Subject — being migrated)

## Purpose

Defines Houston's operational categorization hierarchy for onboarding, Signal routing, and feed personalization.

## Hierarchy

```
Establishment activity description
  → Module (activity type: Hôtel, Restaurant, …)
    → Domain (business scope: Hébergement, Cuisine, …)
      → Subject (problem type: Propreté des chambres, Hygiène HACCP, …)
Unit (optional, orthogonal) → physical location (e.g. Chambre 204)
```

## Core invariants

- Catalogue is backend authority; AI proposes modules only during onboarding.
- Backend expands domains and subjects from catalogue FK tree.
- Unit does not participate in feed subscriptions in MVP.
- `MembershipScope` (RBAC) ≠ `MembershipFeedSubscription` (Ma vue).

## Proposal parent/child rules (§3.1)

| User action | Automatic effect |
| --- | --- |
| Remove module | Remove all domains and subjects under that module |
| Remove domain | Remove all subjects under that domain |
| Add subject | Re-add parent domain and module if missing |
| Add domain | Re-add parent module if missing |

## Signal pivot (V1)

Each Signal carries **one** primary categorization:

- `operational_module`
- `operational_domain`
- `operational_subject`
- optional `operational_unit`

Multiple distinct problems in one Observation → **multiple Signals** after backend validation.

Legacy `detected_domains[]` with confidence scores is **obsolete** for MVP.

## Catalogue source

Authoritative tree: `OnboardingCatalogModule` → `OnboardingCatalogDomain` → `OnboardingCatalogSubject` (DB, seeded migration `0007`).

## Related contracts

- Onboarding/runtime: [`runtime_config_onboarding_domain.md`](runtime_config_onboarding_domain.md)
- Observation → Signals: [`ai_observation_pipeline_contract.md`](ai_observation_pipeline_contract.md)
- Signal categorization: [`signal_domain.md`](signal_domain.md)
- Feed Ma vue: [`feed_subscription_domain.md`](feed_subscription_domain.md)
