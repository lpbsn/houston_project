#!/bin/sh
set -eu

PORT="${PORT:-8080}"
MEDIA_ROOT="${HOUSTON_PRIVATE_MEDIA_ROOT:-/app/apps/api/private_media}"
NGINX_CONF="/tmp/nginx-railway.conf"
DAPHNE_PID=""

cleanup() {
    if [ -n "$DAPHNE_PID" ]; then
        kill "$DAPHNE_PID" 2>/dev/null || true
        wait "$DAPHNE_PID" 2>/dev/null || true
    fi
}

fail() {
    echo "start-api-web: $1" >&2
    cleanup
    exit 1
}

trap cleanup INT TERM

mkdir -p "$MEDIA_ROOT"
chown -R houston:houston "$MEDIA_ROOT" 2>/dev/null || true

cd /app/apps/api

if [ "${DJANGO_DEBUG:-1}" = "0" ]; then
    su -s /bin/sh houston -c "uv run python manage.py check --deploy" || fail "check --deploy failed"
fi

su -s /bin/sh houston -c "uv run daphne -b 127.0.0.1 -p 8000 config.asgi:application" &
DAPHNE_PID=$!

sleep 1
if ! kill -0 "$DAPHNE_PID" 2>/dev/null; then
    fail "Daphne failed to start"
fi

sed "s/__PORT__/${PORT}/g" /app/infra/docker/railway/nginx.conf > "$NGINX_CONF"

nginx -c "$NGINX_CONF" -g "daemon off;" &
NGINX_PID=$!

while kill -0 "$DAPHNE_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
    sleep 1
done

if ! kill -0 "$DAPHNE_PID" 2>/dev/null; then
    kill "$NGINX_PID" 2>/dev/null || true
    wait "$NGINX_PID" 2>/dev/null || true
    fail "Daphne exited unexpectedly"
fi

if ! kill -0 "$NGINX_PID" 2>/dev/null; then
    fail "nginx exited unexpectedly"
fi

cleanup
exit 0
