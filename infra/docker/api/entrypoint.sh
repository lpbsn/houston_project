#!/bin/sh
set -eu

cd /app/apps/api
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
