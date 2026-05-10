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
	@echo "$(GREEN)Users:$(RESET)"
	@echo "  make add-user NAME [NAME...]   — add user(s)"
	@echo "  make remove-user NAME          — remove a user"
	@echo "  make list-users                — list all users"
	@echo "  make show-user NAME            — show user's subscription URL & QR"
	@echo "  make rotate-token NAME         — issue new subscription URL"
	@echo "  make sync                      — re-apply users.json to running xray"
	@echo ""
	@echo "$(GREEN)Operations:$(RESET)"
	@echo "  make backup          — create state backup"
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
	@echo "→ Waiting for services to be healthy..."
	@sleep 10
	@if docker compose ps --format json 2>/dev/null | grep -q '"State":"running"'; then \
		echo "→ Re-syncing users.json to xray runtime..."; \
		docker compose exec -T manager vpn-user sync 2>/dev/null || \
			echo "  (skipped — first run, no users yet)"; \
	fi

.PHONY: down
down: ## Stop all services
	docker compose down

.PHONY: restart
restart: ## Restart all services and re-sync users
	docker compose restart
	@sleep 3
	@echo "→ Re-syncing users to xray runtime..."
	@docker compose exec -T manager vpn-user sync

.PHONY: status
status: ## Show service status
	@docker compose ps

.PHONY: sync
sync: ## Re-apply users.json to running xray (after restart)
	@docker compose exec manager vpn-user sync

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

# ============================================================================
# User management
# ============================================================================

# Catch-all для позиционных аргументов в add-user / remove-user / show-user.
# Make парсит "make add-user alice" как два target'а: add-user, alice.
# Этот rule говорит: для любого target которого мы не знаем — ничего не делать.
# ВАЖНО: побочный эффект — опечатка в имени target (e.g. "make remov-user")
# не выдаст ошибку, тихо ничего не сделает. Будь внимателен.
%:
	@:

.PHONY: add-user
add-user: ## Add user(s). Usage: make add-user alice [bob carol]
	@names="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ -z "$$names" ]; then \
		read -rp "User name(s) (space-separated): " names; \
	fi; \
	if [ -z "$$names" ]; then \
		echo "ERROR: no user names provided" >&2; \
		exit 1; \
	fi; \
	docker compose exec manager vpn-user add $$names

.PHONY: remove-user
remove-user: ## Remove a user. Usage: make remove-user alice
	@name="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ -z "$$name" ]; then \
		read -rp "User name: " name; \
	fi; \
	if [ -z "$$name" ]; then \
		echo "ERROR: no user name provided" >&2; \
		exit 1; \
	fi; \
	docker compose exec manager vpn-user remove $$name

.PHONY: list-users
list-users: ## List all users
	@docker compose exec manager vpn-user list

.PHONY: show-user
show-user: ## Show subscription URL & QR. Usage: make show-user alice
	@name="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ -z "$$name" ]; then \
		read -rp "User name: " name; \
	fi; \
	if [ -z "$$name" ]; then \
		echo "ERROR: no user name provided" >&2; \
		exit 1; \
	fi; \
	docker compose exec manager vpn-user show $$name

.PHONY: rotate-token
rotate-token: ## Issue new subscription URL. Usage: make rotate-token alice
	@name="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ -z "$$name" ]; then \
		read -rp "User name: " name; \
	fi; \
	if [ -z "$$name" ]; then \
		echo "ERROR: no user name provided" >&2; \
		exit 1; \
	fi; \
	docker compose exec manager vpn-user rotate-token $$name

# ============================================================================
# Backup
# ============================================================================

.PHONY: backup
backup: ## Create a state backup
	@sudo /opt/vpn-servers/scripts/backup.sh
	@echo ""
	@echo "→ Latest backups:"
	@sudo ls -lt /var/backups/vpn/ | head -5
