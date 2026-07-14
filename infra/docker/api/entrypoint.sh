#!/bin/sh
set -eu

cd /app/apps/api

if [ "${DJANGO_DEBUG:-1}" = "0" ]; then
  /opt/venv/bin/python manage.py check --deploy
fi

exec /opt/venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application
