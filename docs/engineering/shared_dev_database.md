# Shared-dev database (Lot 0)

Use a **remote PostgreSQL** database shared between developers while keeping Redis, Celery, and private media **local per machine**.

| Mode | Env file | PostgreSQL | Typical commands |
|------|----------|------------|------------------|
| **Local** (default) | `.env` | Docker service `postgres` | `make up-backend`, `make bootstrap-dev` |
| **Shared-dev** | `.env.shared-dev` | Remote host (Neon, etc.) | `make shared-dev-up`, `make shared-dev-bootstrap` |

Never commit `.env.shared-dev`. Use [`.env.shared-dev.example`](../../.env.shared-dev.example) as the template and store real values in **1Password** (team vault).

## Setup (once per developer)

1. Create or obtain the shared PostgreSQL instance (e.g. Neon project).
2. Copy the template:
   ```bash
   cp .env.shared-dev.example .env.shared-dev
   ```
3. Fill `.env.shared-dev` from 1Password — see [Aligned secrets](#aligned-secrets-mandatory) below.
4. Validate Compose merge and DB connectivity:
   ```bash
   make shared-dev-check
   ```
5. First-time stack + migrations + catalogue:
   ```bash
   make shared-dev-bootstrap
   ```
   `shared-dev-bootstrap` does **not** start `celery-beat`. For scheduled jobs (checklist horizon materialization, chat message purge, upload TTL cleanup), start Beat against the **shared-dev** Compose merge — see [Scheduler in shared-dev mode](#scheduler-in-shared-dev-mode). Lazy read-path checklist materialization remains available without Beat.
6. Frontend (unchanged):
   ```bash
   make web-dev
   ```

## Daily workflow

```bash
make shared-dev-up      # redis + api + celery (remote DB)
make web-dev
```

Optional scheduler — **do not** use `make up-scheduler` here (it targets local `.env` only). Use `make shared-dev-up-scheduler` — see [Scheduler in shared-dev mode](#scheduler-in-shared-dev-mode).

After `git pull` with new migrations (coordinate with your teammate — one `migrate` at a time):

```bash
make shared-dev-migrate
```

## Docker Compose: `depends_on` and `!override`

The base [`docker-compose.yml`](../../docker-compose.yml) makes `api`, `celery`, and `celery-beat` depend on local `postgres`.

[`docker-compose.shared-dev.yml`](../../docker-compose.shared-dev.yml) uses **`depends_on: !override`** so the merged config depends on **redis only**. A naive override without `!override` can leave `postgres` in `depends_on` and block startup.

`postgres` is also placed under profile `local-db` as a secondary guard — it must not start in shared-dev.

**Requires Docker Compose v2 with `!override` support** (OrbStack / Docker Desktop 2024+).

### Mandatory validation

Before every `shared-dev-up`, `make` runs [`infra/scripts/assert-shared-dev-compose.sh`](../../infra/scripts/assert-shared-dev-compose.sh), which executes:

```bash
docker compose \
  --profile scheduler \
  --env-file .env.shared-dev \
  -f docker-compose.yml \
  -f docker-compose.shared-dev.yml \
  config --format json
```

The script fails if `api`, `celery`, or `celery-beat` still depend on `postgres`, or if `POSTGRES_HOST` resolves to `postgres` / `localhost` / `127.0.0.1`.

Manual debug:

```bash
docker compose \
  --profile scheduler \
  --env-file .env.shared-dev \
  -f docker-compose.yml \
  -f docker-compose.shared-dev.yml \
  config
```

## Aligned secrets (mandatory)

These **must be identical** for every developer using the shared DB. Store them in 1Password — never in Git, Slack, or issues.

| Variable | Why |
|----------|-----|
| `DJANGO_SECRET_KEY` | Default base for auth token pepper |
| `HOUSTON_AUTH_TOKEN_PEPPER` | Access/refresh token hashing + chat WS tickets |
| `HOUSTON_AUTH_TOKEN_SALT` | If non-default |
| `HOUSTON_CHAT_WS_TICKET_SALT` | If non-default |
| `POSTGRES_*` | Same database for all |
| `HOUSTON_REGISTRATION_INVITE_CODES` | Consistent onboarding tests |

**May differ per developer:** `OPENAI_API_KEY` and other personal AI keys.

## SSL

Set in `.env.shared-dev`:

```bash
POSTGRES_SSLMODE=require
```

Local `.env` omits this (or uses `disable`) — Django reads `POSTGRES_SSLMODE` in [`apps/api/config/settings.py`](../../apps/api/config/settings.py).

## Scheduler in shared-dev mode

`make up-scheduler` runs `$(COMPOSE) up-backend` against **local** `.env` (`docker-compose.yml` only). After `make shared-dev-up`, that target would start local `postgres` and point `api`/`celery-beat` at the wrong database.

Use the dedicated target instead:

```bash
make shared-dev-up-scheduler
```

This runs the same preflight as `shared-dev-up`, ensures `redis` + `api` + `celery` are up against the remote DB, then starts `celery-beat` with the shared-dev Compose merge.

Local dev (`.env`) continues to use `make up-scheduler`.

## Safety guards

| Command | Guard |
|---------|-------|
| `make reset-dev-db` | Refused if `.env` points to shared/remote DB ([`assert-local-dev-db.sh`](../../infra/scripts/assert-local-dev-db.sh)) |
| `make test` | Same — pytest must not run against shared DB |
| `make shared-dev-*` | Requires `.env.shared-dev` + compose preflight |

**There is no `make shared-dev-reset`.** To wipe the shared database, use your cloud provider console (e.g. Neon) deliberately.

## Migration coordination

- Run `make shared-dev-migrate` after pulls that add migrations.
- Avoid two developers running `migrate` at the same time on the shared instance.

## Lot 0 limitations (accepted)

- **Redis / Celery** are local — your worker processes only jobs from your local broker.
- **`private_media`** is a local Docker volume — photo files uploaded on one machine are not on another (DB rows exist, files may 404).
- **Realtime / notifications** unchanged — not part of Lot 0.

## Local vs shared-dev comparison

| | Local `.env` | Shared-dev `.env.shared-dev` |
|---|--------------|------------------------------|
| Postgres | Docker `postgres` service | Remote host |
| Redis | Local Docker | Local Docker |
| Data | Per-machine volume | Shared team data |
| Reset | `make reset-dev-db` | Cloud console only |
| Tests | `make test` | Use local `.env` only |

## References

- Installation: [`INSTALL_MAC.md`](../../INSTALL_MAC.md)
- QA: [`docs/qa/fresh_install_validation.md`](../qa/fresh_install_validation.md)
