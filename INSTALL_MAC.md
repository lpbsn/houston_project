# Installation locale Houston sur macOS

Guide **une fois** pour cloner Houston et lancer l’app sur un Mac. Quotidien après install : [`docs/engineering/local_development.md`](docs/engineering/local_development.md). Smoke : [`docs/deploy/smoke_checklist.md`](docs/deploy/smoke_checklist.md).

**Toutes les commandes** se lancent depuis la racine du dépôt (`README.md`, `Makefile`, `docker-compose.yml`), sauf mention contraire.

| Parcours | Quand | Commandes clés |
|----------|-------|----------------|
| **Machine neuve** | Premier clone | `cp .env.example .env` → `make build-backend` → **`make bootstrap-dev`** → `make web-install` → `make web-dev` |
| **Reset destructif** | Base locale vide | **`make reset-dev-db`** (lire le warning) → éventuellement `make web-install` → `make web-dev` |
| **Quotidien / après `git pull`** | Stack déjà là | **`make bootstrap-dev`** (non destructif) ou `make up-backend` |

- **`make bootstrap-dev`** ne remplace pas **`make build-backend`** ni **`make web-install`**.
- **`make reset-dev-db`** efface la DB Postgres locale et **tous les volumes Docker du projet**. Relancez **`make web-install`** si vous utilisez le conteneur `web`.

## Prérequis

| Outil | Obligatoire |
|-------|-------------|
| Git, Docker Desktop **ou** OrbStack (`docker compose`), Make (`xcode-select --install`) | Oui |
| Node.js 24 + npm (image [`infra/docker/web/Dockerfile`](infra/docker/web/Dockerfile)) | Oui (frontend local) |
| Xcode (Simulateur iOS) / Android Studio | Seulement pour Capacitor local |
| Python 3.13.13 + uv hors Docker | Non si le backend reste dans Docker |

Ports hôte : API **8000**, Vite **5173**, Postgres **5432**, Redis **6379**.

Accès Git : URL SSH réelle de l’équipe. Clé SSH GitHub si besoin (`ssh-keygen`, Settings → SSH keys, `ssh -T git@github.com`).

## Étapes (machine neuve)

1. `cd ~/Projects` (créez le dossier si besoin) puis `git clone <URL_DU_REPO>` et `cd houston_project`.
2. Vérifier : `ls README.md Makefile docker-compose.yml .env.example`.
3. `cp .env.example .env` — remplacer `DJANGO_SECRET_KEY`. **Jamais** de secret ou d’invite dans une variable `VITE_*`.
4. Docker / OrbStack démarré. Première fois : `make build-backend` (plusieurs minutes).
5. `make bootstrap-dev` — `up-backend` → migrate → import catalogue → check. Compte Platform : utilisateur `ACTIVE` puis `docker compose exec api python manage.py grant_platform_operator <email>` ; wizard **desktop** `http://localhost:5173/platform`.
6. Scheduler horizon (optionnel) : `make up-scheduler` — [`docs/engineering/local_development.md`](docs/engineering/local_development.md).
7. Health : `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health/` → **200**.
8. `make web-install` puis `make web-dev` → http://localhost:5173. Ne pas lancer `make up` (conteneur `web`) **et** `make web-dev` en même temps (port 5173).
9. Arrêt : `make down` (Docker) et Ctrl+C sur Vite.

Médias privés : volume Docker `private_media`. Dossier local `apps/api/private_media` seulement hors Docker ou dépannage (`uploads.E001`).

### `.env` minimal

Défauts Compose (hôtes `postgres` / `redis` **dans** le réseau Docker) : `DJANGO_DEBUG=1`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,api`, `HOUSTON_CLIENT_ORIGINS` avec `http://localhost:5173` et `http://127.0.0.1:5173`, `POSTGRES_HOST=postgres` (pas `localhost` pour l’API Docker), Redis `redis://redis:6379/…`.

Optionnel : `OPENAI_API_KEY` (serveur uniquement), `HOUSTON_AI_*`, `VITE_API_BASE_URL=http://localhost:8000` en local (vide = same-origin en prod nginx). Après changement de `.env` : `make recreate-backend`.

## Autres profils

- Frontend dans Docker : `make up` (pas `make web-dev` en parallèle). Rebuild images : `make up-build`.
- Init granulaires : `make migrate` · `make import-catalog` · `make catalog-check` (14 BU / 134 AS catalogue global, pas les instances établissement).
- Types API après pull qui change le contrat : `make schema` puis `make web-api-generate`.
- Après `git pull` : `make build-backend` si Dockerfiles/deps ; sinon `make bootstrap-dev` ; `make web-install` si `package-lock.json` a changé.

Vérifs optionnelles : `make check`, `make web-typecheck`, `make verify`. Quotidien : `make up-backend` + `make web-dev`. Logs : `docker compose logs -f api` / `celery`. Shell API : `make shell`.

## Si ça bloque

| Problème | Action |
|----------|--------|
| Docker pas démarré | Ouvrir OrbStack ou Docker Desktop |
| Port 5173 | Un seul de `make up` / `make web-dev` ; profil npm : `make up-backend` |
| Port 5432 / 6379 / 8000 | Autre Postgres/Redis/dev local — `lsof -i :PORT` |
| `make migrate` / `bootstrap-dev` échoue | `make up-backend` puis réessayer |
| Catalogue vide | `make import-catalog` puis `make catalog-check` |
| `/platform` refusé | Compte `ACTIVE` + `grant_platform_operator` + desktop Web |
| Observations `queued` | `docker compose up -d celery` ; Redis ; optionnel OpenAI |
| `uploads.E001` | Volume `private_media` ; hors Docker `mkdir -p apps/api/private_media` |
| `make web-api-generate` | D’abord `make schema` |
| Secrets | Ne pas coller `docker compose config` (interpolation) |

## Checklist

- [ ] Clone + `.env` avec `DJANGO_SECRET_KEY` local
- [ ] `docker compose ps` : postgres, redis, api, celery **Up**
- [ ] `make bootstrap-dev` + `catalog-check`
- [ ] Health 200 + http://localhost:5173
- [ ] Platform si besoin (`grant_platform_operator`)

| URL | Rôle |
|-----|------|
| http://localhost:5173 | Frontend Vite |
| http://localhost:8000/api/v1/health/ | Health |
| http://localhost:8000/api/docs/ | Swagger (dev) |
| http://localhost:5173/platform | Platform desktop |
| Admin Django | Non installé |

Références : [`README.md`](README.md), [`docs/architecture/authentication_charter.md`](docs/architecture/authentication_charter.md), [`docs/product/domains/runtime_config_onboarding_domain.md`](docs/product/domains/runtime_config_onboarding_domain.md), [`docs/product/domains/ai_observation_pipeline_contract.md`](docs/product/domains/ai_observation_pipeline_contract.md).
