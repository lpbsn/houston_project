# Installation locale Houston sur macOS

## Guide pas à pas (débutant) — toutes les commandes

À faire **une fois** avant de coder : installer sur le Mac **Git**, **Docker Desktop** ou **OrbStack**, **Node.js 24** (https://nodejs.org), et les outils de ligne de commande Apple si `make` manque :

```bash
xcode-select --install
```

Remplacez `<URL_DU_REPO>` par l’URL SSH réelle fournie par votre équipe (ex. `git@github.com:mon-org/houston_project.git`).

### Machine neuve vs reset destructif

| Parcours | Quand l’utiliser | Commandes clés |
|----------|------------------|----------------|
| **Machine neuve** | Premier clone, jamais lancé sur ce Mac | `cp .env.example .env` → `make build` → **`make bootstrap-dev`** → `make web-install` → `make web-dev` |
| **Reset destructif** | Repartir d’une base vide (données locales perdues) | **`make reset-dev-db`** (lire le warning) → éventuellement `make web-install` → `make web-dev` |
| **Quotidien / après `git pull`** | Stack déjà configurée, pas de wipe | **`make bootstrap-dev`** (non destructif, safe à relancer) ou `make up-backend` |

- **`make bootstrap-dev`** ne remplace pas **`make build`** (première install) ni **`make web-install`** (frontend local).
- **`make reset-dev-db`** efface la DB Postgres locale et **tous les volumes Docker du projet** (dont `web_node_modules` si vous utilisez le conteneur `web`). Il ne modifie ni le code ni le `.env`. Relancez **`make web-install`** si le frontend Docker (`make up`) était utilisé.
- Validation E2E documentée : [`docs/qa/fresh_install_validation.md`](docs/qa/fresh_install_validation.md).

---

### Étape 1 — Aller dans un dossier de travail

```bash
cd ~/Projects
```

(Créez le dossier si besoin : `mkdir -p ~/Projects && cd ~/Projects`)

---

### Étape 2 — Cloner le projet

```bash
git clone <URL_DU_REPO>
cd houston_project
```

---

### Étape 3 — Vérifier que vous êtes à la racine du projet

```bash
pwd
ls README.md Makefile docker-compose.yml .env.example
```

Vous devez voir ces fichiers. **Toutes les commandes suivantes** se lancent depuis ce dossier (`houston_project`).

---

### Étape 4 — Créer le fichier de configuration

```bash
cp .env.example .env
```

Ouvrez `.env` dans un éditeur et modifiez au minimum :

- `DJANGO_SECRET_KEY=` → une longue chaîne aléatoire (pas la valeur `replace-me-for-local-dev`)
- `HOUSTON_REGISTRATION_INVITE_CODES=` → un code pour s’inscrire, ex. `dev-invite-2026` (sinon `/onboarding` ne marchera pas)

Ne mettez **jamais** de clé OpenAI ou de code d’invitation dans une variable qui commence par `VITE_`.

---

### Étape 5 — Médias privés (optionnel en Docker)

En Docker, les médias privés sont stockés dans le volume nommé `private_media`. Le dossier local `apps/api/private_media` n’est requis que pour un usage backend hors Docker ou pour du dépannage :

```bash
mkdir -p apps/api/private_media
```

---

### Étape 6 — Démarrer Docker (OrbStack ou Docker Desktop)

Ouvrez l’application **OrbStack** ou **Docker Desktop** et attendez qu’elle indique que Docker est prêt.

Test rapide :

```bash
docker compose version
```

---

### Étape 7 — Construire les images Docker (première fois, plusieurs minutes)

```bash
make build
```

---

### Étape 8 — Initialiser le backend (recommandé)

Une seule commande démarre les services, applique les migrations, importe le catalogue global et vérifie Django + catalogue :

```bash
make bootstrap-dev
```

Équivalent granulaire (si vous préférez étape par étape) :

```bash
make up-backend
make migrate
make import-catalog
make check
make catalog-check
```

Vérifiez que les services tournent :

```bash
docker compose ps
```

Les services `postgres`, `redis`, `api` et `celery` doivent être **Up**. `make catalog-check` doit afficher **14** `CatalogBusinessUnit` et **134** `CatalogActivitySubject`.

### Scheduler optionnel (checklists horizon)

Pour la matérialisation planifiée des assignments partagés (en plus du worker Celery) :

```bash
make up-scheduler
```

`docker compose up -d celery-beat` reste techniquement possible avec `--profile scheduler`, mais c’est une commande non recommandée — `make up-scheduler` démarre d’abord le backend complet.

---

### Étape 9 — Vérifier que l’API répond

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health/
```

Vous devez voir `200`. Sinon : `docker compose logs api --tail=50`

---

### Étape 10 — Installer les dépendances du frontend (première fois)

```bash
make web-install
```

---

### Étape 11 — Lancer le site web en local

Ouvrez un **deuxième terminal**, retournez à la racine du projet :

```bash
cd ~/Projects/houston_project
make web-dev
```

Laissez ce terminal ouvert. Le serveur affiche une URL du type `http://localhost:5173`.

---

### Étape 12 — Ouvrir l’application dans le navigateur

| Quoi ouvrir | Adresse |
|-------------|---------|
| Application | http://localhost:5173 |
| Créer un compte (onboarding) | http://localhost:5173/onboarding |
| Documentation API (Swagger) | http://localhost:8000/api/docs/ |

Sur `/onboarding`, utilisez le **même code** que dans `HOUSTON_REGISTRATION_INVITE_CODES` de votre `.env`.

---

### Étape 13 — Arrêter tout quand vous avez fini

Terminal frontend : `Ctrl+C` pour arrêter `make web-dev`.

Puis à la racine du projet :

```bash
make down
```

---

### Chaque jour : redémarrer le projet en 3 commandes

Terminal 1 (backend) :

```bash
cd ~/Projects/houston_project
make up-backend
```

Terminal 2 (frontend) :

```bash
cd ~/Projects/houston_project
make web-dev
```

Après un `git pull` qui change la base, le catalogue ou l’API :

```bash
cd ~/Projects/houston_project
make bootstrap-dev
```

Pour repartir d’une base vide (destructif — voir warning affiché) :

```bash
make reset-dev-db
make web-install   # si vous utilisez le conteneur web (make up)
make web-dev
```

---

### Si ça bloque (raccourcis)

| Problème | Commande / action |
|----------|-------------------|
| Docker pas démarré | Ouvrir OrbStack ou Docker Desktop |
| Port 5173 déjà pris | Ne pas lancer `make up` en même temps que `make web-dev` ; utiliser seulement `make up-backend` |
| `make migrate` ou `make bootstrap-dev` échoue | `make up-backend` puis réessayer `make bootstrap-dev` |
| Catalogue vide / autocomplete vide | `make import-catalog` puis `make catalog-check` |
| Repartir de zéro (DB locale) | `make reset-dev-db` puis `make web-install` si besoin |
| Inscription refusée | Vérifier `HOUSTON_REGISTRATION_INVITE_CODES` dans `.env`, puis `docker compose up -d --force-recreate api` |

Détails et dépannage : sections 2 à 14 ci-dessous.

---

## 1. Objectif du document

Ce guide permet à un développeur qui découvre le projet de **cloner Houston depuis GitHub** et de **lancer l’application en local sur un MacBook**.

Configuration cible de ce guide :

- **Backend** (API Django, PostgreSQL, Redis, worker Celery) via **Docker Compose**.
- **Frontend** (React/Vite) en **local** avec **Node.js et npm**, depuis `apps/web/`.

Chaque développeur possède **sa propre base PostgreSQL** (volume Docker local `postgres_data`). Les données ne sont pas partagées entre machines, sauf configuration explicite d’une base distante hors de ce guide.

Toutes les commandes sont à exécuter **depuis la racine du dépôt** (répertoire contenant `docker-compose.yml` et `Makefile`), sauf mention contraire.

Références officielles du projet : [`README.md`](README.md), [`Makefile`](Makefile), [`.env.example`](.env.example), [`apps/api/AGENTS.md`](apps/api/AGENTS.md), [`apps/web/AGENTS.md`](apps/web/AGENTS.md).

---

## 2. Prérequis MacBook

### 2.1 Logiciels à installer

| Outil | Version / remarque (d’après le repo) | Obligatoire pour ce guide |
|-------|--------------------------------------|---------------------------|
| **Git** | Récent | Oui |
| **Docker Desktop** ou **OrbStack** (moteur Docker + CLI Compose v2) | Commande `docker compose` | Oui |
| **Make** | Fourni avec Xcode Command Line Tools : `xcode-select --install` | Oui |
| **Node.js** | Image frontend Docker : **Node 24** ([`infra/docker/web/Dockerfile`](infra/docker/web/Dockerfile)). Le `package.json` ne fixe pas de version minimale. | Oui (frontend local) |
| **npm** | Livré avec Node | Oui (frontend local) |
| **Python 3.13.13** + **uv** | Pour outillage backend **hors** Docker ([`apps/api/AGENTS.md`](apps/api/AGENTS.md)). L’image API utilise déjà Python 3.13.13. | Non si vous n’exécutez le backend que dans Docker |

Aucune connexion à l’environnement Docker d’un autre collègue n’est requise : chacun lance sa stack sur son Mac.

### 2.2 Ressources et ports

Docker Compose expose sur la machine hôte :

| Service | Port hôte |
|---------|-----------|
| API Django | **8000** |
| Frontend Vite (local ou conteneur `web`) | **5173** |
| PostgreSQL | **5432** |
| Redis | **6379** |

Assurez-vous qu’aucune autre application n’occupe ces ports (souvent un Postgres ou Redis local déjà installé).

### 2.3 Espace disque

Prévoir plusieurs Go pour les images Docker (Python 3.13, Node 24, Postgres 17, Redis 7) et le volume `postgres_data`.

---

## 3. Accès GitHub et configuration SSH

### 3.1 Vérifier l’accès à l’organisation

1. Demandez l’accès au dépôt GitHub Houston à votre équipe.
2. Notez l’URL du dépôt (SSH ou HTTPS). Exemple SSH : `git@github.com:<ORGANISATION>/houston_project.git` — **remplacez par l’URL réelle**.

### 3.2 Créer une clé SSH (si vous n’en avez pas)

```bash
ssh-keygen -t ed25519 -C "votre.email@exemple.com" -f ~/.ssh/id_ed25519_houston
```

Ajoutez la clé publique dans GitHub : **Settings → SSH and GPG keys → New SSH key** (`~/.ssh/id_ed25519_houston.pub`).

Optionnel — fichier `~/.ssh/config` :

```
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_houston
```

### 3.3 Tester la connexion

```bash
ssh -T git@github.com
```

Réponse attendue : message de bienvenue GitHub (éventuellement « Hi username! »).

---

## 4. Clonage du repo

```bash
cd ~/Projects   # ou le dossier de votre choix
git clone git@github.com:<ORGANISATION>/houston_project.git
cd houston_project
```

Vérifiez la présence des fichiers clés :

```bash
ls README.md Makefile docker-compose.yml .env.example apps/api/manage.py apps/web/package.json
```

---

## 5. Configuration du `.env`

### 5.1 Créer le fichier

```bash
cp .env.example .env
```

Ne commitez **jamais** `.env` (déjà dans [`.gitignore`](.gitignore)).

### 5.2 Médias privés

En Docker, les médias privés sont stockés dans le volume nommé `private_media`. Le dossier local `apps/api/private_media` n’est requis que pour un usage backend hors Docker ou pour du dépannage :

```bash
mkdir -p apps/api/private_media
```

Django peut échouer au `check` si le chemin n’est pas inscriptible (`uploads.E001`).

### 5.3 Variables — lecture minimale pour démarrer

#### Obligatoires pour un stack Docker local fonctionnel

Ces valeurs sont déjà correctes dans `.env.example` pour Compose (hôtes `postgres` / `redis` **à l’intérieur** du réseau Docker) :

| Variable | Rôle |
|----------|------|
| `DJANGO_SECRET_KEY` | Secret Django — remplacez `replace-me-for-local-dev` par une valeur locale |
| `DJANGO_DEBUG` | `1` en dev |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,api` |
| `CSRF_TRUSTED_ORIGINS` | Doit inclure `http://localhost:5173` et `http://127.0.0.1:5173` |
| `POSTGRES_*` | Identifiants DB (défaut `houston` / `houston`) |
| `POSTGRES_HOST` | **`postgres`** (nom du service Compose, ne pas mettre `localhost` pour l’API dans Docker) |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | URLs `redis://redis:6379/...` |

#### Fortement recommandées pour utiliser l’UI produit

| Variable | Rôle |
|----------|------|
| `HOUSTON_REGISTRATION_INVITE_CODES` | Codes d’invitation séparés par des virgules pour l’inscription publique (`/onboarding`). **Vide = inscription désactivée** ([`README.md`](README.md)). Exemple : `HOUSTON_REGISTRATION_INVITE_CODES=dev-invite-2026` |

#### Optionnelles (fonctionnalités avancées / IA)

| Variable | Rôle |
|----------|------|
| `OPENAI_API_KEY` | Clé serveur uniquement — onboarding IA, transcription, pipeline observation → signal |
| `HOUSTON_AI_ONBOARDING_*` | Réglages onboarding IA |
| `HOUSTON_AI_OBSERVATION_*` | Pipeline observation ; défaut `openai` dans `.env.example` |
| `HOUSTON_AI_TRANSCRIPTION_*` | Transcription audio |
| `HOUSTON_AUTH_THROTTLE_*`, `HOUSTON_CACHE_REDIS_URL` | Throttling auth |
| `HOUSTON_PRIVATE_MEDIA_ROOT` | Vide = défaut `apps/api/private_media` dans le conteneur |
| `VITE_API_BASE_URL` | Présent dans `.env.example` ; le client TS utilise `baseUrl: ''` et le **proxy Vite** — utile surtout au service Docker `web` |

**Interdit** : secrets ou codes d’invitation dans des variables `VITE_*` ([`README.md`](README.md), règles AGENTS).

### 5.4 Exemple minimal `.env` pour un associé

```bash
# Après cp .env.example .env, éditez au minimum :
# DJANGO_SECRET_KEY=<chaîne-aléatoire-longue>
# HOUSTON_REGISTRATION_INVITE_CODES=mon-code-dev
```

---

## 6. Lancement backend avec Docker

### 6.1 Construire les images

```bash
docker compose build
```

Équivalent Makefile : `make build`.

### 6.2 Démarrer l’infra et le backend (sans conteneur frontend)

**Profil recommandé** (frontend en npm local) :

```bash
make up-backend
```

Équivalent :

```bash
docker compose up -d postgres redis api celery
```

Attendez que Postgres soit healthy (healthcheck dans [`docker-compose.yml`](docker-compose.yml)).

### 6.3 Vérifier que les conteneurs tournent

```bash
docker compose ps
```

Logs utiles :

```bash
docker compose logs -f api
docker compose logs -f celery
```

### 6.4 Alternative : tout Docker (y compris frontend)

```bash
docker compose up --build
```

ou :

```bash
make up
```

`make up` exécute : `docker compose up --build api celery web` — le frontend sera sur http://localhost:5173 **dans Docker**. **Ne lancez pas en même temps** `make web-dev` (même port 5173).

### 6.5 Arrêter la stack

```bash
make down
# ou
docker compose down
```

---

## 7. Initialisation base de données

### Parcours recommandé (non destructif)

```bash
make bootstrap-dev
```

Enchaîne : `up-backend` → `migrate` → `import-catalog` → `check` → `catalog-check`.

### Étapes granulaires

Avec les conteneurs **api** et **postgres** démarrés :

```bash
make migrate
make import-catalog
make catalog-check
```

- `make migrate` — équivalent : `docker compose exec api python manage.py migrate`.
- `make import-catalog` — charge les CSV versionnés (`docs/catalogue/business_units.csv`, `activity_subjects.csv`) dans **`CatalogBusinessUnit`** et **`CatalogActivitySubject`** (catalogue global v2, autocomplete onboarding). Idempotent : safe à relancer.
- `make catalog-check` — vérifie **14** `CatalogBusinessUnit` et **134** `CatalogActivitySubject` en base (pas les modèles runtime `BusinessUnit` / `ActivitySubject` d’établissement).

### Reset destructif

Pour repartir d’une base Postgres vide sur une machine déjà configurée :

```bash
make reset-dev-db
```

Affiche un warning : suppression DB locale, volumes Docker (dont `web_node_modules`), perte de toutes les données locales. Ne modifie pas le `.env`. Puis `make web-install` si le conteneur `web` était utilisé.

**Premier utilisateur** : pas de `createsuperuser` ni d’admin Django (module admin non installé). Créez un compte via **http://localhost:5173/onboarding** avec un code défini dans `HOUSTON_REGISTRATION_INVITE_CODES`.

---

## 8. Installation frontend

Depuis la racine du projet :

```bash
make web-install
```

Équivalent :

```bash
cd apps/web && npm install
```

### Génération des types API (si nécessaire)

Le fichier [`apps/api/schema.yml`](apps/api/schema.yml) est versionné. Après un `git pull` qui modifie l’API :

```bash
make schema
make web-api-generate
```

- `make schema` — régénère `apps/api/schema.yml` dans le conteneur API.
- `make web-api-generate` — `openapi-typescript` vers `apps/web/src/api/generated/types.ts`.

---

## 9. Lancement frontend

```bash
make web-dev
```

Équivalent : `cd apps/web && npm run dev`.

- **URL** : http://localhost:5173
- Les appels `/api/...` sont proxifiés vers http://localhost:8000 ([`apps/web/vite.config.ts`](apps/web/vite.config.ts)).

Gardez un terminal avec Docker (`api`, `celery`, …) et un terminal avec `make web-dev`.

### Recréer api/celery après modification du `.env`

```bash
docker compose up -d --force-recreate api celery
```

(Documenté dans [`README.md`](README.md) pour le pipeline observation → signal.)

---

## 10. Vérification complète de l’installation

### 10.1 API et documentation

| URL | Attendu |
|-----|---------|
| http://localhost:8000/api/v1/health/ | Réponse OK (test : `houston/core/tests/test_http.py`) |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/api/schema/ | Schéma OpenAPI brut |

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health/
```

Code HTTP **200** attendu.

### 10.2 Contrôles backend (Docker)

```bash
make check
docker compose exec api python manage.py check
```

Worker Celery (observations → signaux) :

```bash
docker compose logs celery --tail=50
```

Sans service **celery**, les observations restent en état `queued` ([`README.md`](README.md)).

### 10.3 Frontend

Ouvrez http://localhost:5173 — page d’accueil / shell auth.

Test onboarding (si codes configurés) : http://localhost:5173/onboarding

### 10.4 Suite de vérification « projet » (optionnelle, plus longue)

```bash
make test
make lint
make web-typecheck
make web-build
```

Vérification agrégée :

```bash
make verify
```

Sous-ensemble sécurité Docker ([`README.md`](README.md)) :

```bash
make docker-verify-security
```

---

## 11. Commandes quotidiennes

| Action | Commande (racine du repo) |
|--------|---------------------------|
| Démarrer backend + worker (sans frontend Docker) | `make up-backend` |
| Démarrer stack complète (API + Celery + frontend Docker) | `make up` |
| Arrêter | `make down` |
| Logs API | `docker compose logs -f api` |
| Shell dans le conteneur API | `make shell` |
| Migrations | `make migrate` |
| Import catalogue global v2 | `make import-catalog` |
| Vérifier catalogue seed (14 BU / 134 AS) | `make catalog-check` |
| Init backend complète (non destructif) | `make bootstrap-dev` |
| Reset DB locale (destructif) | `make reset-dev-db` |
| Tests backend | `make test` |
| Lint backend | `make lint` |
| Frontend dev (local) | `make web-dev` |
| Typecheck frontend | `make web-typecheck` |
| Build frontend | `make web-build` |

Commandes Django custom repérées :

- `python manage.py import_business_unit_catalog` (app `establishments` — aussi `make import-catalog`)
- `python manage.py cleanup_expired_uploads` (app `uploads`)
- `python manage.py dump_establishment_taxonomy` (app `establishments`)

Exécution via Docker : `docker compose exec api python manage.py <commande>`.

---

## 12. Mise à jour après `git pull`

1. Récupérer le code : `git pull`
2. Reconstruire si Dockerfiles/dépendances changent : `docker compose build`
3. Redémarrer + migrations + catalogue : `make bootstrap-dev` (ou `make up-backend` puis `make migrate` + `make import-catalog`)
4. Si contrat API modifié : `make schema` puis `make web-api-generate`
5. Frontend : `make web-install` si `package-lock.json` a changé
6. Si `.env` modifié : `docker compose up -d --force-recreate api celery`
7. Si nouveau besoin médias : en Docker, le volume `private_media` est géré par Compose ; hors Docker, vérifier `apps/api/private_media`

---

## 13. Erreurs fréquentes Mac + solutions

### Docker ne démarre pas / « Cannot connect to the Docker daemon »

- Ouvrez **Docker Desktop** ou **OrbStack** et attendez que le moteur soit prêt.
- Relancez la commande `docker compose`.

### Port déjà utilisé (`bind: address already in use`)

- **5432** : Postgres local — arrêtez le service ou changez le mapping (non documenté par défaut dans le repo).
- **6379** : Redis local — idem.
- **8000** / **5173** : autre serveur dev — `lsof -i :8000` / `lsof -i :5173` puis arrêt du processus.

### Conflit frontend : rien sur 5173 ou mauvaise app

- Vous avez lancé **`make up`** (conteneur `web`) **et** **`make web-dev`** : un seul des deux sur 5173.
- Profil npm local : `make up-backend` (sans service `web`).

### `make migrate` ou `make bootstrap-dev` échoue : conteneur api arrêté

- `make up-backend` puis `make bootstrap-dev`.

### Repartir d’une base vide (destructif)

- `make reset-dev-db` — lit le warning avant exécution.
- Supprime la DB Postgres locale et les volumes Docker du projet (dont `web_node_modules`).
- Relancez `make web-install` si vous utilisez le conteneur frontend Docker (`make up`).
- Le frontend npm local (`make web-dev`) n’est en général pas impacté.

### Permission / uploads / `uploads.E001`

En Docker, les uploads utilisent le volume nommé `private_media`. Valider l’écriture :

```bash
docker compose exec api sh -lc 'python - <<PY
from pathlib import Path
p = Path("private_media/.write-test")
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("ok")
print(p.read_text())
p.unlink()
PY'
docker compose exec api python manage.py check
```

Hors Docker ou dépannage : `mkdir -p apps/api/private_media` puis `chmod u+rwx apps/api/private_media`.

Les notes Linux `user: "${UID}:${GID}"` du README concernent surtout **Linux** ; rarement nécessaire sur Docker Desktop Mac ou OrbStack.

### Inscription `/onboarding` impossible

- Vérifiez `HOUSTON_REGISTRATION_INVITE_CODES` non vide dans `.env`.
- Recréez api après changement : `docker compose up -d --force-recreate api`.

### Observations bloquées en `queued`

- Service **celery** démarré : `docker compose up -d celery`
- Redis accessible (`CELERY_BROKER_URL`)
- Pour tests manuels réalistes : `OPENAI_API_KEY` + `HOUSTON_AI_OBSERVATION_PROVIDER=openai` ([`.env.example`](.env.example))

### `make web-api-generate` échoue

- Fichier manquant : exécutez d’abord `make schema`.
- Vérifiez `apps/api/schema.yml` existe.

### Fuite de secrets

- Ne partagez pas la sortie de `docker compose config` (interpolation des secrets — [`README.md`](README.md)).

---

## 14. Checklist finale « installation OK »

- [ ] `git clone` réussi, branche à jour
- [ ] `.env` créé depuis `.env.example`, `DJANGO_SECRET_KEY` personnalisé
- [ ] `HOUSTON_REGISTRATION_INVITE_CODES` défini si besoin de `/onboarding`
- [ ] Médias privés OK (volume Docker `private_media` en usage Docker ; dossier local `apps/api/private_media` seulement hors Docker / dépannage)
- [ ] `docker compose ps` : `postgres`, `redis`, `api`, `celery` **Up**
- [ ] `make bootstrap-dev` terminé sans erreur (ou `make migrate` + `make import-catalog` + `make catalog-check`)
- [ ] `make catalog-check` → 14 `CatalogBusinessUnit`, 134 `CatalogActivitySubject`
- [ ] http://localhost:8000/api/v1/health/ → 200
- [ ] http://localhost:8000/api/docs/ accessible
- [ ] `make web-install` OK
- [ ] `make web-dev` OK → http://localhost:5173
- [ ] Inscription ou login testé selon le besoin métier
- [ ] (Optionnel) `make check` et `make web-typecheck` OK

---

## URLs locales utiles

| Ressource | URL |
|-----------|-----|
| Frontend (Vite) | http://localhost:5173 |
| API | http://localhost:8000 |
| Health | http://localhost:8000/api/v1/health/ |
| Swagger | http://localhost:8000/api/docs/ |
| OpenAPI JSON/YAML | http://localhost:8000/api/schema/ |
| Onboarding UI | http://localhost:5173/onboarding |
| Admin Django | **Non disponible** (non installé dans le projet) |

## Documentation métier (références)

- Auth : [`docs/architecture/authentication_charter.md`](docs/architecture/authentication_charter.md)
- Erreurs API : [`docs/architecture/api_error_contract.md`](docs/architecture/api_error_contract.md)
- Onboarding : [`docs/product/domains/runtime_config_onboarding_domain.md`](docs/product/domains/runtime_config_onboarding_domain.md)
- Observations / IA : [`docs/product/domains/ai_observation_pipeline_contract.md`](docs/product/domains/ai_observation_pipeline_contract.md)
