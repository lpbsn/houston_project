.PHONY: build up up-backend up-scheduler down check test lint schema shell migrate migrations-check \
	web-install web-dev web-build web-typecheck web-test web-api-generate verify \
	docker-verify-security import-catalog catalog-check bootstrap-dev reset-dev-db \
	shared-dev-up shared-dev-bootstrap shared-dev-migrate shared-dev-check

SHARED_ENV_FILE := .env.shared-dev
SHARED_COMPOSE := docker compose --env-file $(SHARED_ENV_FILE) \
	-f docker-compose.yml -f docker-compose.shared-dev.yml

build:
	docker compose build

up:
	docker compose up --build api celery web

up-backend:
	docker compose up -d postgres redis api celery
	docker compose exec -u 0 api chown -R houston:houston /app/apps/api/private_media

up-scheduler: up-backend
	docker compose --profile scheduler run --rm -u 0 --no-deps -T celery-beat chown -R houston:houston /var/lib/celerybeat
	docker compose --profile scheduler up -d celery-beat

down:
	docker compose down

check:
	docker compose exec api python manage.py check

docker-verify-security:
	docker compose exec api id
	docker compose exec celery id
	docker compose exec api python manage.py check

test:
	@infra/scripts/assert-local-dev-db.sh .env
	docker compose exec api pytest

lint:
	docker compose exec api ruff check .

schema:
	docker compose exec api python manage.py spectacular --file schema.yml

shell:
	docker compose exec api sh

migrate:
	docker compose exec api python manage.py migrate

migrations-check:
	docker compose exec api python manage.py makemigrations --check --dry-run

import-catalog:
	docker compose exec api python manage.py import_business_unit_catalog

catalog-check:
	docker compose exec api python manage.py shell -c "import sys; from houston.establishments.models import CatalogBusinessUnit, CatalogActivitySubject; bu = CatalogBusinessUnit.objects.count(); n = CatalogActivitySubject.objects.count(); (print('catalog-check FAILED: CatalogBusinessUnit=%d (expected 14), CatalogActivitySubject=%d (expected 134)' % (bu, n)), print('Run: make import-catalog'), sys.exit(1)) if bu != 14 or n != 134 else print('catalog-check OK: %d CatalogBusinessUnit, %d CatalogActivitySubject' % (bu, n))"

bootstrap-dev: up-backend migrate import-catalog check catalog-check

reset-dev-db:
	@infra/scripts/assert-local-dev-db.sh .env
	@echo "WARNING: reset-dev-db is destructive."
	@echo "  - Supprime la base PostgreSQL locale (volume postgres_data)."
	@echo "  - Supprime tous les volumes Docker du projet (dont web_node_modules)."
	@echo "  - Toutes les données locales (comptes, établissements, signaux…) seront perdues."
	@echo "  - Après reset, make web-install peut être nécessaire si vous utilisez le conteneur web."
	docker compose down -v --remove-orphans
	$(MAKE) bootstrap-dev

shared-dev-up:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	$(SHARED_COMPOSE) up -d redis api celery
	$(SHARED_COMPOSE) exec -u 0 api chown -R houston:houston /app/apps/api/private_media

shared-dev-migrate:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	$(SHARED_COMPOSE) exec api python manage.py migrate

shared-dev-import-catalog:
	$(SHARED_COMPOSE) exec api python manage.py import_business_unit_catalog

shared-dev-check:
	@test -f $(SHARED_ENV_FILE) || (echo "FATAL: $(SHARED_ENV_FILE) missing. Copy from .env.shared-dev.example and fill from 1Password." >&2; exit 1)
	@infra/scripts/assert-shared-dev-compose.sh $(SHARED_ENV_FILE)
	@if $(SHARED_COMPOSE) ps --status running --services 2>/dev/null | grep -qx api; then \
		$(SHARED_COMPOSE) exec api python manage.py check; \
	else \
		$(SHARED_COMPOSE) run --rm --no-deps api python manage.py check; \
	fi

shared-dev-bootstrap: shared-dev-up shared-dev-migrate shared-dev-import-catalog shared-dev-check
	$(SHARED_COMPOSE) exec api python manage.py shell -c "import sys; from houston.establishments.models import CatalogBusinessUnit, CatalogActivitySubject; bu = CatalogBusinessUnit.objects.count(); n = CatalogActivitySubject.objects.count(); (print('catalog-check FAILED: CatalogBusinessUnit=%d (expected 14), CatalogActivitySubject=%d (expected 134)' % (bu, n)), print('Run: make shared-dev-bootstrap'), sys.exit(1)) if bu != 14 or n != 134 else print('catalog-check OK: %d CatalogBusinessUnit, %d CatalogActivitySubject' % (bu, n))"

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

web-typecheck:
	cd apps/web && npm run typecheck

web-test:
	cd apps/web && npm test

web-api-generate:
	cd apps/web && npm run api:generate

verify:
	$(MAKE) check
	$(MAKE) test
	$(MAKE) lint
	$(MAKE) schema
	$(MAKE) migrations-check
	$(MAKE) web-typecheck
	$(MAKE) web-build
