# ====================================================================
# Onetouch AI+MES - Developer Makefile
# Run `make help` for the full command list.
# ====================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

DOCKER_DIR := infra/docker
COMPOSE    := docker compose -f $(DOCKER_DIR)/docker-compose.yml --env-file $(DOCKER_DIR)/.env

.PHONY: help up down restart logs ps build pull \
        migrate migrate-down migrate-create seed \
        shell-backend shell-frontend shell-db shell-redis \
        psql redis-cli \
        test test-backend test-frontend lint format \
        clean clean-volumes clean-all \
        env

# ---- Help ----------------------------------------------------------
help: ## Show this help
	@echo "Onetouch AI+MES — make targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---- Lifecycle -----------------------------------------------------
env: ## Bootstrap .env from .env.example if missing
	@test -f $(DOCKER_DIR)/.env || (cp $(DOCKER_DIR)/.env.example $(DOCKER_DIR)/.env && \
		echo ".env created from .env.example — review and edit secrets.")

up: env ## Start the dev environment
	cd $(DOCKER_DIR) && docker compose up -d --remove-orphans

down: ## Stop the dev environment (preserve volumes)
	cd $(DOCKER_DIR) && docker compose down --remove-orphans

restart: down up ## Restart the dev environment

logs: ## Tail logs from all services
	cd $(DOCKER_DIR) && docker compose logs -f --tail=200

ps: ## Show running services
	cd $(DOCKER_DIR) && docker compose ps

build: ## Rebuild service images
	cd $(DOCKER_DIR) && docker compose build

pull: ## Pull latest base images
	cd $(DOCKER_DIR) && docker compose pull --ignore-pull-failures

# ---- Database / migrations ----------------------------------------
migrate: ## Apply DB migrations (alembic upgrade head)
	docker exec onetouch-backend alembic upgrade head

migrate-down: ## Roll back one DB migration
	docker exec onetouch-backend alembic downgrade -1

migrate-create: ## Create a new migration: make migrate-create m="add user table"
	docker exec onetouch-backend alembic revision --autogenerate -m "$(m)"

seed: ## Load initial master data
	bash scripts/seed.sh

# ---- Shells --------------------------------------------------------
shell-backend: ## Open a bash shell inside the backend container
	docker exec -it onetouch-backend bash

shell-frontend: ## Open a sh shell inside the frontend container
	docker exec -it onetouch-frontend sh

shell-db: ## Open a psql shell on the postgres container
	docker exec -it onetouch-postgres psql -U onetouch -d onetouch_mes

shell-redis: ## Open a redis-cli shell
	docker exec -it onetouch-redis redis-cli

psql: shell-db   ## Alias for shell-db
redis-cli: shell-redis ## Alias for shell-redis

# ---- Testing / linting --------------------------------------------
test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests (pytest)
	docker exec onetouch-backend pytest -q

test-frontend: ## Run frontend tests
	docker exec onetouch-frontend pnpm test

lint: ## Lint backend (ruff) and frontend (eslint)
	-docker exec onetouch-backend ruff check .
	-docker exec onetouch-frontend pnpm lint

format: ## Format backend (ruff) and frontend (prettier)
	-docker exec onetouch-backend ruff format .
	-docker exec onetouch-frontend pnpm format

# ---- Cleanup -------------------------------------------------------
clean: ## Remove stopped containers and dangling images
	docker system prune -f

clean-volumes: ## DESTRUCTIVE — remove all named volumes (data loss)
	cd $(DOCKER_DIR) && docker compose down -v --remove-orphans

clean-all: clean-volumes clean ## DESTRUCTIVE — full reset
	@echo "Environment fully reset."
