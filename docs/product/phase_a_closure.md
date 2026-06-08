> **DOCUMENT HISTORIQUE (v1 — Module/Domain/Subject)**  
> Ne pas utiliser comme source produit active.  
> Modèle v1 obsolète. Vérité actuelle : BusinessUnit / ActivitySubject.  
> Onboarding : Manual V2 uniquement (AI onboarding retiré du produit).  
> Voir : [`taxonomy_v1_to_v2_migration.md`](taxonomy_v1_to_v2_migration.md), [`domains/business_unit_taxonomy_domain.md`](domains/business_unit_taxonomy_domain.md), [`domains/runtime_config_onboarding_domain.md`](domains/runtime_config_onboarding_domain.md).

# Phase A Closure — Sujet / Taxonomie opérationnelle

Status: **historical — closed A8 (2026-05-29)**  
Gate: **Phase B/C authorized** — onboarding/runtime taxonomy only (see constraints below)

## Checklist

| # | Livrable | Status |
| --- | --- | --- |
| A1 | v1 onboarding catalogue seed (6 modules, 31 domaines, 154 sujets) | Done — migrated to DB (`0007`) |
| A2 | Typos / labels normalisés | Done |
| A3 | Catalogue target spec (removed; superseded by v2 BusinessUnit seed) | Done (historical) |
| A4 | Mapping legacy → nouveau (catalogue_target §4) | Done |
| A5 | Legacy taxonomy domain specification | Done (historical) |
| A6 | [`feed_subscription_domain.md`](domains/feed_subscription_domain.md) | Done — doc only (V5) |
| A7 | Docs transverses alignées | Done — observation, action, execution feed personal, runtime onboarding, AI observation pipeline, archive feed sorting, AGENTS.md |
| A8 | Clôture signée par humain | **Done — 2026-05-29** |

## Decisions actées

- **V1** : 1 Signal = 1 catégorisation principale module/domain/subject ; multi-problèmes Observation → N Signals.
- **V2** : FK Django `catalog_module`, `catalog_domain`, `operational_module`, `operational_domain`.
- **V3** : Remplacement propre des seeds catalogue legacy ; Units conservées.
- **V4** : Aucun code applicatif avant validation humaine Phase A (A8).
- **V5** : `MembershipFeedSubscription` — contrat doc only ; code interdit avant Phase 4 Signal/Feed.

## Cross-cutting rules (Phase A corpus)

| Topic | Rule |
| --- | --- |
| Hierarchy | Module → Domaine → Sujet ; Unit orthogonal (location) |
| Onboarding AI | Modules-only ; backend expansion domaines + sujets ; proposal v2 |
| Observation | Raw input ; pipeline → 0..N CandidateSignals |
| Signal | One triplet per Signal ; multi-problem Observation → N Signals |
| Action | Inherits parent Signal taxonomy |
| Signal Feed Ma vue | `MembershipFeedSubscription` match (module/domain/subject) |
| Signal Feed general | All active establishment Signals |
| Execution Feed Ma vue | Assigned responsibilities — **not** feed subscriptions |
| RBAC | `MembershipScope` ≠ feed subscriptions |

## Activation minimum sujets (décision Phase A)

- ≥1 active `OperationalModule`
- ≥3 active `OperationalDomain`
- ≥1 active `OperationalSubject` per active domain that remains in the proposal after apply

## Human sign-off (A8)

- [x] Product/architecture reviewer confirms Phase A doc corpus aligned
- [x] No contradictions with `detected_domains` / RBAC-as-feed-filter remain in authoritative docs
- [x] Explicit authorization to begin Phase B/C (onboarding/runtime taxonomy only)

**Signed by:** Human validation (product owner)  
**Date:** 2026-05-29

## Phase B/C constraints (post-A8)

| Rule | Detail |
| --- | --- |
| Stash allowed | **`bc-onboarding-taxonomy` only** |
| Stashes forbidden | `provisioning-signup-hors-scope`, `bc-ai-onboarding-infra` — remain isolated |
| Scope B/C | Onboarding/runtime taxonomy in `establishments/` only |
| Forbidden B/C | Signal, Signal Feed, `MembershipFeedSubscription`, Execution Feed |
| OpenAPI / clients | Regenerate `schema.yml` and `types.ts` **only after** onboarding/runtime API stabilization |
| Deliverables | Migrations/tests onboarding ; UI sujets |

## Next step — Phase B/C

1. Restore stash **`bc-onboarding-taxonomy`** only.
2. Run migrations/tests for establishments onboarding.
3. Finalize UI sujets.
4. Regenerate `schema.yml` and TypeScript client after API stabilization.
5. Do **not** implement Signal/Feed/subscriptions until Phase 4 build plan gate.
6. Do **not** restore provisioning or `bc-ai-onboarding-infra` stashes.
