#!/usr/bin/env sh
# Tests infra guard scripts (no database required).
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

ASSERT_LOCAL="$ROOT_DIR/infra/scripts/assert-local-dev-db.sh"
ASSERT_SHARED="$ROOT_DIR/infra/scripts/assert-shared-dev-compose.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

pass=0
fail=0

assert_ok() {
  label="$1"
  shift
  if "$@"; then
    printf 'PASS: %s\n' "$label"
    pass=$((pass + 1))
  else
    printf 'FAIL: %s\n' "$label" >&2
    fail=$((fail + 1))
  fi
}

assert_fail() {
  label="$1"
  shift
  if "$@"; then
    printf 'FAIL: %s (expected non-zero exit)\n' "$label" >&2
    fail=$((fail + 1))
  else
    printf 'PASS: %s\n' "$label"
    pass=$((pass + 1))
  fi
}

ENV_LOCAL="$TMP_DIR/env.local"
ENV_REMOTE="$TMP_DIR/env.remote"
ENV_SHARED="$TMP_DIR/.env.shared-dev"

cat >"$ENV_LOCAL" <<'EOF'
HOUSTON_DEV_DB_MODE=local
POSTGRES_HOST=postgres
POSTGRES_DB=houston
POSTGRES_USER=houston
POSTGRES_PASSWORD=houston
EOF

cat >"$ENV_REMOTE" <<'EOF'
HOUSTON_DEV_DB_MODE=local
POSTGRES_HOST=ep-test.neon.tech
POSTGRES_DB=houston
POSTGRES_USER=houston
POSTGRES_PASSWORD=houston
EOF

cat >"$ENV_SHARED" <<'EOF'
POSTGRES_HOST=ep-test.neon.tech
POSTGRES_DB=houston
POSTGRES_USER=houston
POSTGRES_PASSWORD=houston
POSTGRES_SSLMODE=require
EOF

# assert-local-dev-db: local .env accepted
assert_ok "local .env accepted" "$ASSERT_LOCAL" "$ENV_LOCAL"

# assert-local-dev-db: remote .env refused
assert_fail "remote .env refused" "$ASSERT_LOCAL" "$ENV_REMOTE"

# assert-local-dev-db: shell POSTGRES_HOST remote refused
assert_fail "shell POSTGRES_HOST override refused" \
  env POSTGRES_HOST=ep-test.neon.tech "$ASSERT_LOCAL" "$ENV_LOCAL"

# assert-local-dev-db: shared-dev env file refused
assert_fail ".env.shared-dev filename refused" "$ASSERT_LOCAL" "$ENV_SHARED"

# assert-shared-dev-compose: valid shared-dev merge
assert_ok "shared-dev compose merge valid" "$ASSERT_SHARED" "$ENV_SHARED"

printf '\ninfra-check: %s passed, %s failed\n' "$pass" "$fail"
if [ "$fail" -ne 0 ]; then
  exit 1
fi
