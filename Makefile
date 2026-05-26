.PHONY: build up down check test lint schema shell migrate

build:
	docker compose build

up:
	docker compose up --build

down:
	docker compose down

check:
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
