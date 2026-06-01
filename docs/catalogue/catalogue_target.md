# Catalogue cible — Module → Domaine → Sujet

Status: authoritative  
Source: [`arborescence.csv`](arborescence.csv)  
Last reviewed: 2026-05-29

## Statistics (gate Phase B)

| Level | Count |
| --- | --- |
| Modules | 6 |
| Domains | 31 |
| Subjects | 154 |
| Units (legacy seed) | unchanged — orthogonal |

Recount command: parse `arborescence.csv` unique `module_key`, `domain_key`, `subject_key`.

## Key convention

| Level | Pattern | Example |
| --- | --- | --- |
| Module | `{module_slug}` | `hotel`, `restaurant`, `retail_commerce` |
| Domain | `{module_slug}__{domain_slug}` | `hotel__hebergement` |
| Subject | `{module_slug}__{domain_slug}__{subject_slug}` | `hotel__hebergement__proprete_des_chambres` |

Labels are French display strings. Keys are scoped; homonymous labels (e.g. « Propreté », « RH & planning ») are unique by key.

## Module keys

| Label | Key |
| --- | --- |
| Hôtel | `hotel` |
| Restaurant | `restaurant` |
| Retail / Commerce | `retail_commerce` |
| Coworking / Bureau | `coworking_bureau` |
| Salle de sport | `salle_de_sport` |
| Loisirs | `loisirs` |

## Seed replacement policy (V3)

Legacy catalogue seeds from migration `0005_seed_onboarding_catalogs.py` are **fully replaced** for modules and domains. No hybrid coexistence.

### Modules removed

| Legacy key | Action |
| --- | --- |
| `bar` | Removed — Bar is a domain under Restaurant |
| `rooftop` | Removed |
| `seminar_rooms` | Removed |

### Modules added

| Key | Label |
| --- | --- |
| `retail_commerce` | Retail / Commerce |
| `salle_de_sport` | Salle de sport |
| `loisirs` | Loisirs |

### Modules kept (label update)

| Key | New label |
| --- | --- |
| `hotel` | Hôtel |
| `restaurant` | Restaurant |
| `coworking_bureau` | Coworking / Bureau (legacy runtime key `coworking` migrated in data migration if present) |

### Domains removed (functional legacy)

All flat functional domain keys (`housekeeping`, `maintenance`, `cleaning`, `security`, `guest_experience`, `kitchen`, `restaurant_room`, `pricing`, `event_management`, `management`) are **removed** from catalogue. Their semantics are distributed as business domains + subjects in the CSV tree.

### Units

`OnboardingCatalogUnit` seed unchanged. Units are orthogonal to Module/Domain/Subject and not used for feed subscriptions in MVP.

## Django FK names (V2)

- `OnboardingCatalogDomain.catalog_module`
- `OnboardingCatalogSubject.catalog_domain`
- `OperationalDomain.operational_module`
- `OperationalSubject.operational_domain`

## Exception policy

No production establishments with legacy runtime data exist in MVP pilot scope. If legacy `OperationalDomain` rows reference removed catalogue keys, Phase B data migration deactivates orphaned runtime rows on draft establishments only.
