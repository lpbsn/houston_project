#!/usr/bin/env sh
# Refuses local-only operations when Compose would target a remote database.
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

file_postgres_host=""

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    \#*) continue ;;
    POSTGRES_HOST=*)
      file_postgres_host="$(printf '%s' "$line" | cut -d= -f2- | tr '[:upper:]' '[:lower:]' | tr -d ' \"')"
      ;;
  esac
done <"$ENV_FILE"

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
    echo "  Use .env with POSTGRES_HOST=postgres for local Docker Postgres." >&2
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
  echo "  Use .env with POSTGRES_HOST=postgres for local Docker Postgres." >&2
  exit 1
fi

printf 'local-dev-db OK: effective POSTGRES_HOST=%s\n' "$effective_postgres_host"
