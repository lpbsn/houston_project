#!/usr/bin/env sh
# Refuses destructive or polluting operations when the env targets a shared/remote database.
set -eu

ENV_FILE="${1:-.env}"
LOCAL_POSTGRES_HOSTS="postgres localhost 127.0.0.1"

if [ ! -f "$ENV_FILE" ]; then
  echo "FATAL: $ENV_FILE not found." >&2
  exit 1
fi

basename_env="$(basename "$ENV_FILE")"
if [ "$basename_env" = ".env.shared-dev" ]; then
  echo "FATAL: $ENV_FILE is for shared-dev only." >&2
  echo "  Do not run reset-dev-db or make test with the shared-dev env file." >&2
  echo "  Use .env for local Docker Postgres (POSTGRES_HOST=postgres)." >&2
  exit 1
fi

houston_mode=""
postgres_host=""

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    \#*) continue ;;
    HOUSTON_DEV_DB_MODE=*)
      houston_mode="$(printf '%s' "$line" | cut -d= -f2- | tr '[:upper:]' '[:lower:]' | tr -d ' \"')"
      ;;
    POSTGRES_HOST=*)
      postgres_host="$(printf '%s' "$line" | cut -d= -f2- | tr '[:upper:]' '[:lower:]' | tr -d ' \"')"
      ;;
  esac
done <"$ENV_FILE"

if [ "$houston_mode" = "shared" ]; then
  echo "FATAL: HOUSTON_DEV_DB_MODE=shared in $ENV_FILE." >&2
  echo "  reset-dev-db and make test are local-only operations." >&2
  echo "  Use .env with POSTGRES_HOST=postgres for local development." >&2
  exit 1
fi

if [ -n "$postgres_host" ]; then
  is_local=0
  for host in $LOCAL_POSTGRES_HOSTS; do
    if [ "$postgres_host" = "$host" ]; then
      is_local=1
      break
    fi
  done
  if [ "$is_local" -eq 0 ]; then
    echo "FATAL: POSTGRES_HOST=$postgres_host in $ENV_FILE (remote database)." >&2
    echo "  reset-dev-db only wipes local Docker volumes — it does not reset a remote DB." >&2
    echo "  make test must not run against a shared database." >&2
    echo "  Restore POSTGRES_HOST=postgres in .env for local work." >&2
    exit 1
  fi
fi
