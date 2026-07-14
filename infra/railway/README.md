# Houston Railway — config as code wiring

Railway does **not** auto-discover multiple `railway.toml` files under subdirectories. Each application service must reference its config file explicitly.

## Shared monorepo

Houston builds from the **repository root** (all Dockerfiles copy `pyproject.toml`, `apps/api/`, `apps/web/`, etc.).

| Setting | `api-web` | `celery-worker` | `celery-beat` |
|---|---|---|---|
| **Root Directory** | `/` | `/` | `/` |
| **Config File path** | `/infra/railway/api-web/railway.toml` | `/infra/railway/celery-worker/railway.toml` | `/infra/railway/celery-beat/railway.toml` |

Do **not** set Root Directory to `infra/railway/<service>` — that narrows the build context and breaks Docker builds.

## Watch Paths (build triggers)

Railway evaluates `watchPatterns` from the **repository root** (`/`), even when Root Directory is `/`. Patterns are anchored with a leading `/`.

Watch Paths express **functional build dependencies** — what should trigger a redeploy — not the full context currently included by `COPY . /app` in today's Dockerfiles. A future Docker COPY alignment (PR3) will narrow the build context to match this matrix.

| Service | `watchPatterns` |
|---|---|
| `api-web` | `/apps/web/**`, `/contracts/**`, `/apps/api/**`, `/infra/docker/railway/**`, `/infra/railway/api-web/**`, `/pyproject.toml`, `/uv.lock`, `/.dockerignore`, `/README.md` (temporary) |
| `celery-worker` | `/apps/api/**`, `/infra/docker/api/**`, `/infra/railway/celery-worker/**`, `/pyproject.toml`, `/uv.lock`, `/.dockerignore`, `/README.md` (temporary) |
| `celery-beat` | `/apps/api/**`, `/infra/docker/api/**`, `/infra/railway/celery-beat/**`, `/pyproject.toml`, `/uv.lock`, `/.dockerignore`, `/README.md` (temporary) |

`/README.md` is temporary: current Dockerfiles still `COPY` it for the `uv sync` layer. It will be removed from `watchPatterns` in PR3 when that `COPY` is dropped.

> Le dashboard peut afficher une valeur différente, car Railway ne le met pas à jour depuis `railway.toml`. Pour chaque déploiement, la configuration en code prévaut. Vérifier la configuration effective dans les détails du déploiement via l'icône de fichier.

Full trigger matrix and validation scenarios: [`docs/deploy/railway_deploy_contract.md`](../../docs/deploy/railway_deploy_contract.md#build-triggers-watch-paths).

## Setup (once per Railway project)

1. Create a Railway project from the Houston GitHub repository.
2. Add **PostgreSQL** and **Redis** plugins (private).
3. Add three services from the same repo: `api-web`, `celery-worker`, `celery-beat`.
4. For each service: **Settings → Source → Root Directory** = `/` (default).
5. For each service: **Settings → Config File** = absolute path from the table above.
6. On the deployment details page, confirm the config-file icon points to the expected `railway.toml`.
7. Configure variables per [`docs/deploy/railway_variables.md`](../../docs/deploy/railway_variables.md).
8. Follow the full playbook: [`docs/deploy/railway_deploy_contract.md`](../../docs/deploy/railway_deploy_contract.md).

## Config overrides dashboard

Values in these TOML files override dashboard build/deploy settings for each deployment. Dashboard values are not updated automatically — the repo is the source of truth.

## Related

* [`docs/deploy/railway_deploy_contract.md`](../../docs/deploy/railway_deploy_contract.md) — operational contract
* [`docs/deploy/railway_architecture.md`](../../docs/deploy/railway_architecture.md) — architecture overview
