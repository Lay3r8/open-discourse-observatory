SHELL := /bin/sh
COMPOSE ?= ./scripts/compose.sh
UV ?= uv
MISE ?= mise
UVRUN ?= ./scripts/uv-run.sh

.PHONY: setup doctor bootstrap up down adminer migrate import-pilot gdelt-sample test lint format db-check reset-db

setup:
	command -v $(MISE) >/dev/null 2>&1 || { echo "mise is required"; exit 127; }
	command -v $(UV) >/dev/null 2>&1 || { echo "uv is required"; exit 127; }
	$(MISE) install
	$(MISE) exec -- $(UV) sync --extra dev
	test -f .env || cp .env.example .env

doctor:
	./scripts/doctor.sh

bootstrap: setup doctor up migrate import-pilot db-check

up:
	$(COMPOSE) up -d --wait --wait-timeout 60 postgres

down:
	$(COMPOSE) down

adminer:
	$(COMPOSE) --profile tools up -d adminer

migrate:
	$(UVRUN) python -m odo.cli migrate

import-pilot:
	$(UVRUN) python -m odo.cli import-pilot

gdelt-sample:
	$(UVRUN) python -m odo.cli gdelt-file tests/fixtures/gdelt_sample.tsv --timestamp 20260101000000

test:
	$(UVRUN) pytest -q

lint:
	$(UVRUN) ruff check src tests

format:
	$(UVRUN) ruff format src tests

db-check:
	$(UVRUN) python -m odo.cli db-check

reset-db:
	$(COMPOSE) down -v
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) import-pilot
	$(MAKE) db-check
