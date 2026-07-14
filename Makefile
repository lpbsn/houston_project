.PHONY: \
	build build-backend build-web build-prod-test-web \
	up up-build up-backend up-scheduler up-prod-test down-prod-test migrate-prod-test restart-backend recreate-backend down \
	check test lint schema schema-check shell migrate migrations-check \
	backend-lint backend-migrations-check backend-schema backend-schema-check backend-deploy-check backend-test backend-check backend-rebuild \
	web-install web-dev web-build web-typecheck web-lint web-test web-api-generate web-api-generate-check web-check \
	verify local-check docker-verify-security infra-check \
	import-catalog catalog-check bootstrap-dev reset-dev-db assert-local-dev-db clean-operational-test-data

# -----------------------------------------------------------------------------
# Compose / env
# -----------------------------------------------------------------------------

COMPOSE := docker compose
COMPOSE_PROD_TEST := $(COMPOSE) -f docker-compose.prod-test.yml -p houston-prod-test
API_EXEC := $(COMPOSE) exec -T api
API_EXEC_INTERACTIVE := $(COMPOSE) exec api
API_CMD := $(API_EXEC) sh -lc
API_DIR := /app/apps/api

WEB_DIR := apps/web

PYTEST_MARKERS := not openai_observation_smoke and not openai_smoke and not slow
PYTEST_ARGS := -m "$(PYTEST_MARKERS)" -q
# Optional extra pytest args, e.g. make backend-test PYTEST_EXTRA_ARGS="houston/action_plans/tests/test_schedule_api.py -k staff"
PYTEST_EXTRA_ARGS ?=
ifdef ARGS
PYTEST_EXTRA_ARGS := $(ARGS)
endif

# -----------------------------------------------------------------------------
# Docker lifecycle
# -----------------------------------------------------------------------------

build-backend:
	DOCKER_BUILDKIT=1 $(COMPOSE) --profile scheduler build api celery celery-beat

build-web:
	$(COMPOSE) build web

build: build-backend build-web

up: assert-local-dev-db
	$(COMPOSE) up api celery web

up-build: assert-local-dev-db
	$(COMPOSE) up --build api celery web

up-backend: assert-local-dev-db
	$(COMPOSE) up -d postgres redis api celery
	$(COMPOSE) exec -u 0 api chown -R houston:houston /app/apps/api/private_media

# Simple process restart (bind-mounted code). Does not reload .env or image.
restart-backend:
	$(COMPOSE) restart api celery
	@if $(COMPOSE) --profile scheduler ps --status running --services 2>/dev/null | grep -qx celery-beat; then \
		$(COMPOSE) --profile scheduler restart celery-beat; \
	fi

# Recreate api/celery (--no-deps: postgres/redis untouched) to reload .env.
recreate-backend: assert-local-dev-db
	$(COMPOSE) up -d --force-recreate --no-deps api celery
	@if $(COMPOSE) --profile scheduler ps --status running --services 2>/dev/null | grep -qx celery-beat; then \
		$(COMPOSE) --profile scheduler up -d --force-recreate --no-deps celery-beat; \
	fi

# Celery Beat (profile scheduler): action-plan schedule horizon, chat purge, upload TTL cleanup.
# Not started by bootstrap-dev — run explicitly after local bootstrap.
up-scheduler: assert-local-dev-db up-backend
	$(COMPOSE) --profile scheduler run --rm -u 0 --no-deps -T celery-beat chown -R houston:houston /var/lib/celerybeat
	$(COMPOSE) --profile scheduler up -d celery-beat

down:
	$(COMPOSE) down

# -----------------------------------------------------------------------------
# Prod-test local stack (PR3) — gateway on :8080, static SPA + API same-origin
# -----------------------------------------------------------------------------

build-prod-test-web:
	docker build -f infra/docker/web/Dockerfile -t houston-web:prod .

up-prod-test: assert-local-dev-db
	$(COMPOSE_PROD_TEST) up --build -d gateway
	@echo ""
	@echo "Prod-test gateway: http://localhost:8080"
	@echo "First boot: make migrate-prod-test"

migrate-prod-test: assert-local-dev-db
	$(COMPOSE_PROD_TEST) exec -T api sh -lc 'cd /app/apps/api && /opt/venv/bin/python manage.py migrate'

down-prod-test:
	$(COMPOSE_PROD_TEST) down

shell:
	$(API_EXEC_INTERACTIVE) sh

# -----------------------------------------------------------------------------
# Local safety
# -----------------------------------------------------------------------------

assert-local-dev-db:
	@infra/scripts/assert-local-dev-db.sh .env

infra-check:
	@infra/scripts/test-dev-guards.sh

# -----------------------------------------------------------------------------
# Backend — Docker only
# -----------------------------------------------------------------------------

check:
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py check'

lint:
	$(MAKE) backend-lint

test: assert-local-dev-db
	$(MAKE) backend-test

schema:
	$(MAKE) backend-schema

schema-check:
	$(MAKE) backend-schema-check

migrate: assert-local-dev-db
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py migrate'

migrations-check:
	$(MAKE) backend-migrations-check

backend-lint:
	$(API_CMD) 'cd $(API_DIR) && uv run ruff check .'

backend-migrations-check:
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py makemigrations --check --dry-run'

backend-schema:
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py spectacular --file schema.yml'

backend-schema-check: backend-schema
	git diff --exit-code apps/api/schema.yml

backend-deploy-check:
	$(API_CMD) 'cd $(API_DIR) && DJANGO_DEBUG=0 \
	  DJANGO_SECRET_KEY=deploy-check-secret-with-sufficient-length-and-entropy \
	  DJANGO_ALLOWED_HOSTS=example.railway.app \
	  CSRF_TRUSTED_ORIGINS=https://example.railway.app \
	  HOUSTON_AUTH_TOKEN_PEPPER=deploy-check-pepper-distinct \
	  HOUSTON_AUTH_TOKEN_SALT=deploy-check-auth-salt \
	  HOUSTON_CHAT_WS_TICKET_SALT=deploy-check-chat-salt \
	  HOUSTON_REALTIME_WS_TICKET_SALT=deploy-check-realtime-salt \
	  OPENAI_API_KEY=sk-deploy-check \
	  HOUSTON_PRIVATE_MEDIA_ROOT=/tmp/houston-deploy-check-media \
	  uv run python manage.py check --deploy'

backend-test: assert-local-dev-db
	$(API_CMD) 'cd $(API_DIR) && uv run pytest $(PYTEST_ARGS) $(PYTEST_EXTRA_ARGS)'

backend-check: check backend-lint backend-migrations-check backend-schema-check backend-test

backend-rebuild: down build-backend up-backend

docker-verify-security:
	$(API_EXEC) id
	$(COMPOSE) exec -T celery id
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py check'

# -----------------------------------------------------------------------------
# Catalog / bootstrap local
# -----------------------------------------------------------------------------

import-catalog: assert-local-dev-db
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py import_business_unit_catalog'

catalog-check:
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py verify_catalog_counts'

bootstrap-dev: assert-local-dev-db up-backend migrate import-catalog check catalog-check
	@echo ""
	@echo "Optional: run 'make up-scheduler' to start celery-beat (action-plan schedule horizon, chat purge, upload TTL)."
	@echo "Lazy read-path materialization remains available without Beat."

reset-dev-db: assert-local-dev-db
	@echo "WARNING: reset-dev-db is destructive."
	@echo "  - Supprime la base PostgreSQL locale (volume postgres_data)."
	@echo "  - Supprime tous les volumes Docker du projet (dont web_node_modules)."
	@echo "  - Toutes les données locales (comptes, établissements, signaux…) seront perdues."
	@echo "  - Après reset, make web-install peut être nécessaire si vous utilisez le conteneur web."
	$(COMPOSE) down -v --remove-orphans
	$(MAKE) bootstrap-dev

clean-operational-test-data: assert-local-dev-db
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py clean_operational_test_data $(ARGS)'

# -----------------------------------------------------------------------------
# Frontend — native Mac
# -----------------------------------------------------------------------------

web-install:
	cd $(WEB_DIR) && npm install

web-dev:
	cd $(WEB_DIR) && npm run dev

web-build:
	cd $(WEB_DIR) && npm run build

web-typecheck:
	cd $(WEB_DIR) && npm run typecheck

web-lint:
	cd $(WEB_DIR) && npm run lint

web-test:
	cd $(WEB_DIR) && npm test

web-api-generate:
	cd $(WEB_DIR) && npm run api:generate

web-api-generate-check:
	cd $(WEB_DIR) && npm run api:generate
	git diff --exit-code apps/web/src/api/generated/types.ts

web-check: web-test web-typecheck web-build web-api-generate-check

# -----------------------------------------------------------------------------
# Full validation
# -----------------------------------------------------------------------------

local-check: backend-check web-check

verify: local-check
