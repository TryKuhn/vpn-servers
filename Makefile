# ============================================================================
#  vpn-servers — Makefile
# ============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

CYAN  := \033[0;36m
GREEN := \033[0;32m
RESET := \033[0m

# ============================================================================

.PHONY: help
help: ## Show this help
	@echo ""
	@echo "$(CYAN)vpn-servers$(RESET) — operator commands"
	@echo ""
	@echo "$(GREEN)Setup:$(RESET)"
	@echo "  make install         — bootstrap a fresh server (apt, docker, ufw)"
	@echo "  make init            — generate Reality keys into .env"
	@echo ""
	@echo "$(GREEN)Lifecycle:$(RESET)"
	@echo "  make up              — start all services (builds manager if needed)"
	@echo "  make down            — stop all services"
	@echo "  make restart         — restart all services"
	@echo "  make status          — show service status"
	@echo "  make logs            — tail logs from all services"
	@echo "  make logs-xray       — tail xray logs only"
	@echo "  make logs-manager    — tail manager logs only"
	@echo ""
	@echo "$(GREEN)Development:$(RESET)"
	@echo "  make rebuild-manager — rebuild manager image after code changes"
	@echo "  make shell-manager   — open shell inside manager container"
	@echo ""
	@echo "$(GREEN)Diagnostics:$(RESET)"
	@echo "  make config-check    — validate the rendered xray config"
	@echo ""

# ============================================================================
# Setup
# ============================================================================

.PHONY: install
install: ## Bootstrap a fresh server (run once on a new VPS)
	@bash scripts/install.sh

.PHONY: init
init: .env ## Generate Reality keys into .env
	@bash scripts/generate-keys.sh

.env: .env.example
	@if [ ! -f .env ]; then \
		echo "→ Copying .env.example to .env..."; \
		cp .env.example .env; \
		chmod 600 .env; \
		echo "✓ Created .env. Edit it before running 'make init'."; \
		exit 1; \
	fi

# ============================================================================
# Lifecycle
# ============================================================================

.PHONY: up
up: ## Start all services
	docker compose up -d --build
	@echo ""
	@echo "✓ Services starting. Check status with: make status"

.PHONY: down
down: ## Stop all services
	docker compose down

.PHONY: restart
restart: ## Restart all services
	docker compose restart

.PHONY: status
status: ## Show service status
	@docker compose ps

.PHONY: logs
logs: ## Tail logs from all services (Ctrl+C to exit)
	docker compose logs -f

.PHONY: logs-xray
logs-xray: ## Tail xray logs only
	docker compose logs -f xray

.PHONY: logs-manager
logs-manager: ## Tail manager logs only
	docker compose logs -f manager

# ============================================================================
# Development
# ============================================================================

.PHONY: rebuild-manager
rebuild-manager: ## Rebuild manager image after code changes
	docker compose build manager
	docker compose up -d --no-deps manager
	@echo "✓ Manager rebuilt and restarted."

.PHONY: shell-manager
shell-manager: ## Open bash shell inside manager container
	docker compose exec manager /bin/bash

# ============================================================================
# Diagnostics
# ============================================================================

.PHONY: config-check
config-check: ## Validate the rendered xray config
	@if [ ! -f data/xray/config.json ]; then \
		echo "ERROR: data/xray/config.json not found. Run 'make up' first."; \
		exit 1; \
	fi
	@docker run --rm -v $$(pwd)/data/xray:/etc/xray:ro teddysun/xray \
		xray -test -config /etc/xray/config.json
	@echo "✓ Config is valid."
