#!/usr/bin/env sh
# Houston readonly smoke — health, same-origin routing, SPA shell.
#
# Usage:
#   BASE_URL=https://<railway-domain> ./scripts/smoke/readonly.sh
#   BASE_URL=http://localhost:8080 ./scripts/smoke/readonly.sh   # after make up-prod-test
#
# Requires: curl, grep. No auth. Never commit credentials.
# Exit 0 on success, non-zero on first failure.
set -eu

usage() {
  cat <<'EOF'
Houston readonly smoke checks (no auth, no secrets).

Usage:
  BASE_URL=<origin> ./scripts/smoke/readonly.sh

Examples:
  BASE_URL=http://localhost:8080 ./scripts/smoke/readonly.sh
  BASE_URL=https://houston-prod-test.up.railway.app ./scripts/smoke/readonly.sh

Checks:
  GET /api/v1/health/           → 200 + {"status":"ok"}
  GET /signals                    → SPA shell (id="root")
  GET /api/foo                    → NOT SPA HTML
  GET /ws/v1/.../realtime/        → NOT SPA HTML

Manual / sign-off only: worker logs, auth, cache headers, OpenAI pipeline.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

BASE_URL="${BASE_URL:-}"
if [ -z "$BASE_URL" ]; then
  echo "ERROR: BASE_URL is required." >&2
  usage >&2
  exit 1
fi

BASE_URL="${BASE_URL%/}"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

ok() {
  echo "OK: $1"
}

assert_no_spa_html() {
  path="$1"
  body="$2"
  if printf '%s' "$body" | grep -q 'id="root"'; then
    fail "GET ${path} returned SPA HTML"
  fi
}

body="$(curl -fsS "${BASE_URL}/api/v1/health/")" || fail "GET /api/v1/health/"
printf '%s' "$body" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' \
  || fail "GET /api/v1/health/ missing {\"status\":\"ok\"}"
ok "GET /api/v1/health/"

body="$(curl -fsS "${BASE_URL}/signals")" || fail "GET /signals"
printf '%s' "$body" | grep -q 'id="root"' || fail "GET /signals missing SPA shell"
ok "GET /signals (SPA shell)"

body="$(curl -sS "${BASE_URL}/api/foo" 2>/dev/null || true)"
assert_no_spa_html "/api/foo" "$body"
ok "GET /api/foo (not SPA)"

body="$(curl -sS "${BASE_URL}/ws/v1/establishments/00000000-0000-0000-0000-000000000000/realtime/" 2>/dev/null || true)"
assert_no_spa_html "/ws/v1/.../realtime/" "$body"
ok "GET /ws/v1/.../realtime/ (not SPA)"

echo "All readonly smoke checks passed."
