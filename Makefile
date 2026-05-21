.PHONY: help test lint agents-install agents-test services-build

help:
	@echo "Available targets:"
	@echo "  agents-install  - Install agent dependencies"
	@echo "  agents-test     - Run agent unit tests"
	@echo "  agents-lint     - Lint agent code"
	@echo "  services-build  - Build all service Docker images"
	@echo "  up              - Start local docker-compose stack"
	@echo "  down            - Stop local docker-compose stack"

agents-install:
	cd agents && uv sync --all-extras

agents-test:
	cd agents && uv run pytest tests/ -v

agents-lint:
	cd agents && uv run ruff check src/ tests/

services-build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down
