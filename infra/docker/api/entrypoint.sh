#!/bin/sh
set -eu

cd /app/apps/api
exec python manage.py runserver 0.0.0.0:8000
