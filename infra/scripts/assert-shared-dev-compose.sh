#!/usr/bin/env sh
# Validates merged docker-compose config for shared-dev mode:
# - api/celery/celery-beat must depend on redis only (not postgres)
# - POSTGRES_HOST must not be the local Compose service name "postgres"
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${1:-.env.shared-dev}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.shared-dev.yml"

if [ ! -f "$ENV_FILE" ]; then
  echo "FATAL: $ENV_FILE not found. Copy from .env.shared-dev.example and fill from 1Password." >&2
  exit 1
fi

CONFIG_JSON="$(docker compose --profile scheduler --env-file "$ENV_FILE" $COMPOSE_FILES config --format json)" || {
  echo "FATAL: docker compose config failed." >&2
  exit 1
}

export CONFIG_JSON
python3 <<'PY'
import json
import os
import sys

cfg = json.loads(os.environ["CONFIG_JSON"])
services = cfg.get("services", {})

LOCAL_POSTGRES_HOSTS = {"postgres", "localhost", "127.0.0.1"}
WORKERS = ("api", "celery", "celery-beat")


def depends_on_names(service_name: str) -> list[str]:
    deps = services.get(service_name, {}).get("depends_on")
    if deps is None:
        return []
    if isinstance(deps, list):
        return deps
    if isinstance(deps, dict):
        return list(deps.keys())
    return []


errors: list[str] = []

for name in WORKERS:
    if name not in services:
        errors.append(f"{name} missing from merged compose config (use --profile scheduler)")
        continue
    dep_names = depends_on_names(name)
    if "postgres" in dep_names:
        errors.append(f"{name} still depends_on postgres after merge (got: {dep_names})")
    if "redis" not in dep_names:
        errors.append(f"{name} must depend_on redis (got: {dep_names})")

api_env = services.get("api", {}).get("environment", {})
postgres_host = ""
if isinstance(api_env, dict):
    postgres_host = str(api_env.get("POSTGRES_HOST", "")).strip().lower()
elif isinstance(api_env, list):
    for item in api_env:
        if isinstance(item, str) and item.startswith("POSTGRES_HOST="):
            postgres_host = item.split("=", 1)[1].strip().lower()
            break

if not postgres_host:
    errors.append("POSTGRES_HOST missing from api environment in merged config")
elif postgres_host in LOCAL_POSTGRES_HOSTS:
    errors.append(
        f"POSTGRES_HOST={postgres_host!r} in merged config — shared-dev requires a remote host"
    )

if errors:
    print("FATAL: shared-dev compose validation failed:", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    print(
        "\nRun: docker compose --profile scheduler --env-file .env.shared-dev "
        "-f docker-compose.yml -f docker-compose.shared-dev.yml config",
        file=sys.stderr,
    )
    print("Fix: ensure depends_on: !override in docker-compose.shared-dev.yml", file=sys.stderr)
    sys.exit(1)

print(
    f"shared-dev compose OK: api/celery/celery-beat → redis only; "
    f"POSTGRES_HOST={postgres_host}"
)
PY
