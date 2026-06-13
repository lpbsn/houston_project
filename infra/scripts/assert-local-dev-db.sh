#!/usr/bin/env sh
# Refuses local-only operations when Compose would target a shared/remote database.
# Validates effective POSTGRES_HOST from `docker compose config`, not just the env file.
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${1:-.env}"
LOCAL_POSTGRES_HOSTS="postgres localhost 127.0.0.1"

if [ ! -f "$ENV_FILE" ]; then
  echo "FATAL: $ENV_FILE not found." >&2
  exit 1
fi

basename_env="$(basename "$ENV_FILE")"
if [ "$basename_env" = ".env.shared-dev" ]; then
  echo "FATAL: $ENV_FILE is for shared-dev only." >&2
  echo "  Do not run local-only targets with the shared-dev env file." >&2
  echo "  Use .env for local Docker Postgres (POSTGRES_HOST=postgres)." >&2
  exit 1
fi

houston_mode=""
file_postgres_host=""

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    \#*) continue ;;
    HOUSTON_DEV_DB_MODE=*)
      houston_mode="$(printf '%s' "$line" | cut -d= -f2- | tr '[:upper:]' '[:lower:]' | tr -d ' \"')"
      ;;
    POSTGRES_HOST=*)
      file_postgres_host="$(printf '%s' "$line" | cut -d= -f2- | tr '[:upper:]' '[:lower:]' | tr -d ' \"')"
      ;;
  esac
done <"$ENV_FILE"

if [ "$houston_mode" = "shared" ]; then
  echo "FATAL: HOUSTON_DEV_DB_MODE=shared in $ENV_FILE." >&2
  echo "  Local-only operations require .env with POSTGRES_HOST=postgres." >&2
  echo "  Use make shared-dev-* for remote database work." >&2
  exit 1
fi

is_local_host() {
  host="$1"
  for local_host in $LOCAL_POSTGRES_HOSTS; do
    if [ "$host" = "$local_host" ]; then
      return 0
    fi
  done
  return 1
}

if [ -n "${POSTGRES_HOST:-}" ]; then
  shell_postgres_host="$(printf '%s' "$POSTGRES_HOST" | tr '[:upper:]' '[:lower:]' | tr -d ' \"')"
  if ! is_local_host "$shell_postgres_host"; then
    echo "FATAL: POSTGRES_HOST=$shell_postgres_host in shell environment (overrides $ENV_FILE)." >&2
    echo "  Unset POSTGRES_HOST or use a local host: $LOCAL_POSTGRES_HOSTS" >&2
    echo "  For shared-dev, use make shared-dev-* with .env.shared-dev." >&2
    exit 1
  fi
fi

CONFIG_JSON="$(docker compose --env-file "$ENV_FILE" -f docker-compose.yml config --format json)" || {
  echo "FATAL: docker compose config failed for $ENV_FILE." >&2
  exit 1
}

export CONFIG_JSON
effective_postgres_host="$(python3 <<'PY'
import json
import os

cfg = json.loads(os.environ["CONFIG_JSON"])
api_env = cfg.get("services", {}).get("api", {}).get("environment", {})
host = ""
if isinstance(api_env, dict):
    host = str(api_env.get("POSTGRES_HOST", "")).strip().lower()
elif isinstance(api_env, list):
    for item in api_env:
        if isinstance(item, str) and item.startswith("POSTGRES_HOST="):
            host = item.split("=", 1)[1].strip().lower()
            break
print(host or "postgres")
PY
)"

if ! is_local_host "$effective_postgres_host"; then
  echo "FATAL: effective POSTGRES_HOST=$effective_postgres_host (docker compose config with --env-file $ENV_FILE)." >&2
  if [ -n "$file_postgres_host" ] && [ "$file_postgres_host" != "$effective_postgres_host" ]; then
    echo "  $ENV_FILE has POSTGRES_HOST=$file_postgres_host (overridden by shell or Compose defaults)." >&2
  elif [ -n "$file_postgres_host" ]; then
    echo "  $ENV_FILE has POSTGRES_HOST=$file_postgres_host." >&2
  fi
  echo "  Local-only operations require POSTGRES_HOST in: $LOCAL_POSTGRES_HOSTS" >&2
  echo "  For shared-dev, use make shared-dev-* with .env.shared-dev." >&2
  exit 1
fi

printf 'local-dev-db OK: effective POSTGRES_HOST=%s\n' "$effective_postgres_host"
