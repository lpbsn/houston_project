#!/bin/sh
set -eu

cd /app/apps/api

if [ "${DJANGO_DEBUG:-1}" = "0" ]; then
  uv run python manage.py check --deploy
fi

exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
