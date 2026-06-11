.PHONY: \
	build up up-backend up-scheduler down \
	check test lint schema schema-check shell migrate migrations-check \
	backend-lint backend-migrations-check backend-schema backend-schema-check backend-test backend-check \
	web-install web-dev web-build web-typecheck web-test web-api-generate web-check \
	verify local-check docker-verify-security \
	import-catalog catalog-check bootstrap-dev reset-dev-db assert-local-dev-db \
	shared-dev-up shared-dev-bootstrap shared-dev-migrate shared-dev-import-catalog shared-dev-check

# -----------------------------------------------------------------------------
# Compose / env
# -----------------------------------------------------------------------------

COMPOSE := docker compose
API_EXEC := $(COMPOSE) exec -T api
API_EXEC_INTERACTIVE := $(COMPOSE) exec api
API_CMD := $(API_EXEC) sh -lc
API_DIR := /app/apps/api

WEB_DIR := apps/web

PYTEST_MARKERS := not openai_observation_smoke and not openai_smoke and not slow
PYTEST_ARGS := -m "$(PYTEST_MARKERS)" -q

SHARED_ENV_FILE := .env.shared-dev
SHARED_COMPOSE := $(COMPOSE) --env-file $(SHARED_ENV_FILE) \
	-f docker-compose.yml -f docker-compose.shared-dev.yml

# -----------------------------------------------------------------------------
# Docker lifecycle
# -----------------------------------------------------------------------------

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up --build api celery web

up-backend:
	$(COMPOSE) up -d postgres redis api celery
	$(COMPOSE) exec -u 0 api chown -R houston:houston /app/apps/api/private_media

up-scheduler: up-backend
	$(COMPOSE) --profile scheduler run --rm -u 0 --no-deps -T celery-beat chown -R houston:houston /var/lib/celerybeat
	$(COMPOSE) --profile scheduler up -d celery-beat

down:
	$(COMPOSE) down

shell:
	$(API_EXEC_INTERACTIVE) sh

# -----------------------------------------------------------------------------
# Local safety
# -----------------------------------------------------------------------------

assert-local-dev-db:
	@infra/scripts/assert-local-dev-db.sh .env

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

backend-test: assert-local-dev-db
	$(API_CMD) 'cd $(API_DIR) && uv run pytest $(PYTEST_ARGS)'

backend-check: check backend-lint backend-migrations-check backend-schema-check backend-test

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
	$(API_CMD) 'cd $(API_DIR) && uv run python manage.py shell -c "import sys; from houston.establishments.models import CatalogBusinessUnit, CatalogActivitySubject; bu = CatalogBusinessUnit.objects.count(); n = CatalogActivitySubject.objects.count(); (print(\"catalog-check FAILED: CatalogBusinessUnit=%d (expected 14), CatalogActivitySubject=%d (expected 134)\" % (bu, n)), print(\"Run: make import-catalog\"), sys.exit(1)) if bu != 14 or n != 134 else print(\"catalog-check OK: %d CatalogBusinessUnit, %d CatalogActivitySubject\" % (bu, n))"'

bootstrap-dev: assert-local-dev-db up-backend migrate import-catalog check catalog-check

reset-dev-db: assert-local-dev-db
	@echo "WARNING: reset-dev-db is destructive."
	@echo "  - Supprime la base PostgreSQL locale (volume postgres_data)."
	@echo "  - Supprime tous les volumes Docker du projet (dont web_node_modules)."
	@echo "  - Toutes les données locales (comptes, établissements, signaux…) seront perdues."
	@echo "  - Après reset, make web-install peut être nécessaire si vous utilisez le conteneur web."
	$(COMPOSE) down -v --remove-orphans
	$(MAKE) bootstrap-dev

# -----------------------------------------------------------------------------
# Shared-dev — explicit only
# -----------------------------------------------------------------------------

shared-dev-up:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	$(SHARED_COMPOSE) up -d redis api celery
	$(SHARED_COMPOSE) exec -u 0 api chown -R houston:houston /app/apps/api/private_media

shared-dev-migrate:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	$(SHARED_COMPOSE) exec -T api sh -lc 'cd $(API_DIR) && uv run python manage.py migrate'

shared-dev-import-catalog:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	$(SHARED_COMPOSE) exec -T api sh -lc 'cd $(API_DIR) && uv run python manage.py import_business_unit_catalog'

shared-dev-check:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	@if $(SHARED_COMPOSE) ps --status running --services 2>/dev/null | grep -qx api; then \
		$(SHARED_COMPOSE) exec -T api sh -lc 'cd $(API_DIR) && uv run python manage.py check'; \
	else \
		$(SHARED_COMPOSE) run --rm --no-deps -T api sh -lc 'cd $(API_DIR) && uv run python manage.py check'; \
	fi

shared-dev-bootstrap: shared-dev-up shared-dev-migrate shared-dev-import-catalog shared-dev-check
	$(SHARED_COMPOSE) exec -T api sh -lc 'cd $(API_DIR) && uv run python manage.py shell -c "import sys; from houston.establishments.models import CatalogBusinessUnit, CatalogActivitySubject; bu = CatalogBusinessUnit.objects.count(); n = CatalogActivitySubject.objects.count(); (print(\"catalog-check FAILED: CatalogBusinessUnit=%d (expected 14), CatalogActivitySubject=%d (expected 134)\" % (bu, n)), print(\"Run: make shared-dev-bootstrap\"), sys.exit(1)) if bu != 14 or n != 134 else print(\"catalog-check OK: %d CatalogBusinessUnit, %d CatalogActivitySubject\" % (bu, n))"'

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

web-test:
	cd $(WEB_DIR) && npm test

web-api-generate:
	cd $(WEB_DIR) && npm run api:generate

web-check: web-test web-typecheck web-build

# -----------------------------------------------------------------------------
# Full validation
# -----------------------------------------------------------------------------

local-check: backend-check web-check

verify: local-check