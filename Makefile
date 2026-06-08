.PHONY: build up up-backend down check test lint schema shell migrate migrations-check \
	web-install web-dev web-build web-typecheck web-api-generate verify \
	docker-verify-security import-catalog catalog-check bootstrap-dev reset-dev-db

build:
	docker compose build

up:
	docker compose up --build api celery web

up-backend:
	docker compose up -d postgres redis api celery

down:
	docker compose down

check:
	docker compose exec api python manage.py check

docker-verify-security:
	docker compose exec api id
	docker compose exec celery id
	docker compose exec api python manage.py check

test:
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
	@echo "WARNING: reset-dev-db is destructive."
	@echo "  - Supprime la base PostgreSQL locale (volume postgres_data)."
	@echo "  - Supprime tous les volumes Docker du projet (dont web_node_modules)."
	@echo "  - Toutes les données locales (comptes, établissements, signaux…) seront perdues."
	@echo "  - Après reset, make web-install peut être nécessaire si vous utilisez le conteneur web."
	docker compose down -v --remove-orphans
	$(MAKE) bootstrap-dev

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

web-typecheck:
	cd apps/web && npm run typecheck

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
