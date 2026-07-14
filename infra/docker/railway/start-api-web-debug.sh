#!/bin/sh
set -eu

STATUS=0

finish() {
  echo "=== start-api-web-debug: exit status=${STATUS} ==="
  echo "=== sleeping 3600s for log inspection ==="
  sleep 3600
}

trap finish EXIT

cd /app/apps/api

echo "=== start-api-web-debug: safe env ==="
echo "DJANGO_DEBUG=${DJANGO_DEBUG:-<unset>}"
echo "DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-<unset>}"
echo "CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS:-<unset>}"
echo "POSTGRES_DB=${POSTGRES_DB:-<unset>}"
echo "POSTGRES_USER=${POSTGRES_USER:-<unset>}"
echo "POSTGRES_HOST=${POSTGRES_HOST:-<unset>}"
echo "POSTGRES_PORT=${POSTGRES_PORT:-<unset>}"
echo "POSTGRES_SSLMODE=${POSTGRES_SSLMODE:-<unset>}"
if [ -n "${REDIS_URL:-}" ]; then
  echo "REDIS_URL=$(printf '%s' "$REDIS_URL" | sed -E \
    's#(redis://[^:/@]*):[^@]*@#\1:***@#; s#redis://:[^@]*@#redis://:***@#')"
else
  echo "REDIS_URL=<unset>"
fi
echo "=== end safe env ==="

if ! /opt/venv/bin/python manage.py check --deploy; then
  STATUS=1
fi

if ! /opt/venv/bin/python manage.py migrate --verbosity 3; then
  STATUS=1
fi

exit "$STATUS"
