.PHONY: build up down check test lint schema shell migrate migrations-check \
	web-install web-dev web-build web-typecheck web-api-generate verify \
	docker-verify-security

build:
	docker compose build

up:
	docker compose up --build api celery web

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
