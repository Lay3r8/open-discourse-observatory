SHELL := /bin/sh
DC ?= docker compose

.PHONY: up down adminer build shell migrate import-pilot gdelt-sample test lint format db-check reset-db

up:
	$(DC) up -d --build postgres etl

down:
	$(DC) down

adminer:
	$(DC) --profile tools up -d adminer

build:
	$(DC) build etl

shell:
	$(DC) exec etl sh

migrate:
	$(DC) exec etl python -m odo.cli migrate

import-pilot:
	$(DC) exec etl python -m odo.cli import-pilot

gdelt-sample:
	$(DC) exec etl python -m odo.cli gdelt-file tests/fixtures/gdelt_sample.tsv --timestamp 20260101000000

test:
	$(DC) exec etl pytest -q

lint:
	$(DC) exec etl ruff check src tests

format:
	$(DC) exec etl ruff format src tests

db-check:
	$(DC) exec postgres psql -U $${POSTGRES_USER:-discourse} -d $${POSTGRES_DB:-discourse} -c "select (select count(*) from research.incident) incidents, (select count(*) from research.source) sources, (select count(*) from research.coding_decision) coding_decisions;"

reset-db:
	$(DC) down -v
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) import-pilot
