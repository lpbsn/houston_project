# Fresh install — validation

## Statut

| Champ | Valeur |
|-------|--------|
| Date | 2026-06 |
| `make verify` | Vert |
| Fresh install | Validé manuellement depuis base Docker vide |
| Parcours E2E | Validé manuellement |

## Prérequis

- Docker Desktop ou OrbStack
- Fichier `.env` (copie de `.env.example`) avec au minimum :
  - `DJANGO_SECRET_KEY` personnalisé
  - `HOUSTON_REGISTRATION_INVITE_CODES` pour `/onboarding`
- Médias privés : en Docker, volume nommé `private_media` (géré par Compose). Le dossier local `apps/api/private_media` n’est requis que hors Docker ou pour du dépannage.
- Images Docker construites (`make build`) — première install uniquement

## Séquences

### Machine neuve (premier clone)

```bash
cp .env.example .env
make build
make bootstrap-dev
make web-install
make web-dev
```

Scheduler optionnel (checklists horizon) : `make up-scheduler`.

`make bootstrap-dev` enchaîne : `up-backend` → `migrate` → `import-catalog` → `check` → `catalog-check`.

### Reset destructif (repartir d’une base vide)

```bash
make reset-dev-db
make web-install   # si le conteneur web Docker (make up) était utilisé
make web-dev
```

`make reset-dev-db` affiche un warning, supprime la DB Postgres locale et les volumes Docker du projet, puis relance `make bootstrap-dev`.

## Vérifications automatiques

| Commande | Attendu |
|----------|---------|
| `make bootstrap-dev` | Exit 0 |
| `make catalog-check` | `catalog-check OK: 14 CatalogBusinessUnit, 134 CatalogActivitySubject` |
| `make check` | Aucune erreur Django |
| `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health/` | `200` |
| `make import-catalog` | Message `Catalog import complete` (counts created/updated selon état DB) |

Le catalogue global est chargé dans **`CatalogBusinessUnit`** et **`CatalogActivitySubject`** via `import_business_unit_catalog` à partir des CSV versionnés :

- [`docs/catalogue/business_units.csv`](../catalogue/business_units.csv)
- [`docs/catalogue/activity_subjects.csv`](../catalogue/activity_subjects.csv)

`catalog-check` ne vérifie **pas** les modèles runtime `BusinessUnit` / `ActivitySubject` (créés à l’onboarding par établissement).

## Parcours E2E validé (manuel)

1. Inscription ou login (`/onboarding` avec code invite)
2. Création organisation / établissement
3. Onboarding manuel v2
4. Activation de l’établissement
5. Soumission observation (texte, photo optionnelle)
6. Signal visible dans le feed (worker Celery requis)
7. Action depuis le signal
8. Action visible dans l’execution feed

Checklist opérationnelle courte : [`pilot_smoke_checklist.md`](pilot_smoke_checklist.md).

## Hors scope de ce document

- Pas de modification du comportement produit
- OpenAI optionnel pour un pipeline observation réaliste (`OPENAI_API_KEY`, `HOUSTON_AI_OBSERVATION_PROVIDER=openai`) — voir [`README.md`](../../README.md)
- `make verify` n’inclut pas migrate ni import catalogue

## Références

- Installation Mac : [`INSTALL_MAC.md`](../../INSTALL_MAC.md)
- Catalogue v2 : [`business_unit_taxonomy_domain.md`](../product/domains/business_unit_taxonomy_domain.md)
- Makefile : `import-catalog`, `catalog-check`, `bootstrap-dev`, `reset-dev-db`
