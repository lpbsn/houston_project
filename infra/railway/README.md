# Houston Railway — config as code wiring

Railway does **not** auto-discover multiple `railway.toml` files under subdirectories. Each application service must reference its config file explicitly.

## Shared monorepo

Houston builds from the **repository root**. Dockerfiles use selective `COPY` aligned with Watch Paths (e.g. `apps/api/`, `pyproject.toml`, `uv.lock`; `api-web` also copies frontend build inputs).

| Setting | `api-web` | `celery-worker` | `celery-beat` |
|---|---|---|---|
| **Root Directory** | `/` | `/` | `/` |
| **Config File path** | `/infra/railway/api-web/railway.toml` | `/infra/railway/celery-worker/railway.toml` | `/infra/railway/celery-beat/railway.toml` |

Do **not** set Root Directory to `infra/railway/<service>` — that narrows the build context and breaks Docker builds.

## Watch Paths (build triggers)

Railway evaluates `watchPatterns` from the **repository root** (`/`), even when Root Directory is `/`. Patterns are anchored with a leading `/`.

Watch Paths express **functional build dependencies** — what should trigger a redeploy. Dockerfiles use selective `COPY` aligned with this matrix.

| Service | `watchPatterns` |
|---|---|
| `api-web` | `/apps/web/**`, `/contracts/operational-realtime-invalidation.json`, `/apps/api/**`, `/infra/docker/railway/**`, `/infra/railway/api-web/**`, `/pyproject.toml`, `/uv.lock`, `/.dockerignore` |
| `celery-worker` | `/apps/api/**`, `/contracts/operational-realtime-invalidation.json`, `/infra/docker/api/**`, `/infra/railway/celery-worker/**`, `/pyproject.toml`, `/uv.lock`, `/.dockerignore` |
| `celery-beat` | `/apps/api/**`, `/contracts/operational-realtime-invalidation.json`, `/infra/docker/api/**`, `/infra/railway/celery-beat/**`, `/pyproject.toml`, `/uv.lock`, `/.dockerignore` |

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

## Wait for CI (operator checklist)

Enable only after PR2 merge. Full procedure: [`docs/deploy/railway_deploy_contract.md#wait-for-ci-post-merge-pr2`](../../docs/deploy/railway_deploy_contract.md#wait-for-ci-post-merge-pr2).

1. Confirm **Config File path** per service (table above) on deployment details (config-file icon).
2. **Test first, prod second:** enable Wait for CI on a Railway test project / non-prod branch before production.
3. **Workflows Railway waits for on each commit** (workflows, not individual job names — no manual job list on Railway):
   * [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) — always triggered
   * [`.github/workflows/docker-smoke.yml`](../../.github/workflows/docker-smoke.yml) — only when Docker-related paths change
4. GitHub branch protection (GitHub-only): required checks are `backend-tests`, `frontend-tests`, `docs-check`; `docker-smoke.yml` is path-filtered and not required in branch protection.
5. Dashboard Wait for CI / Watch Paths may differ from repo config — deployment details config-file icon is the effective source.

## Related

* [`docs/deploy/railway_deploy_contract.md`](../../docs/deploy/railway_deploy_contract.md) — operational contract
* [`docs/deploy/railway_architecture.md`](../../docs/deploy/railway_architecture.md) — architecture overview
