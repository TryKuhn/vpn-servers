# ============================================================================
#  vpn-servers — Makefile
# ============================================================================
#
#  Common operator commands. Usage:  make <command>
#  Run `make help` to see everything.
# ============================================================================

# Default goal when running just `make`
.DEFAULT_GOAL := help

# Use bash for recipes (more predictable than /bin/sh on different distros)
SHELL := /bin/bash

# Pretty colors for help output
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
	@echo "  make install       — bootstrap a fresh server (apt, docker, ufw)"
	@echo "  make init          — generate Reality keys into .env"
	@echo ""
	@echo "$(GREEN)Lifecycle:$(RESET)"
	@echo "  make up            — start the VPN server"
	@echo "  make down          — stop the VPN server"
	@echo "  make restart       — restart"
	@echo "  make status        — show container status"
	@echo "  make logs          — tail xray logs (Ctrl+C to exit)"
	@echo ""
	@echo "$(GREEN)Diagnostics:$(RESET)"
	@echo "  make config-check  — validate the rendered config"
	@echo "  make ps            — list running containers"
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

# Convenience: create .env from .env.example if it doesn't exist yet.
# Marks itself as a target so it can be a prerequisite of `init`.
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
up: ## Start the VPN server
	docker compose up -d
	@echo ""
	@echo "✓ Server starting. Check status with: make status"

.PHONY: down
down: ## Stop the VPN server
	docker compose down

.PHONY: restart
restart: ## Restart the VPN server
	docker compose restart

.PHONY: status
status: ## Show container status
	@docker compose ps

.PHONY: logs
logs: ## Tail xray logs (Ctrl+C to exit)
	docker compose logs -f xray

.PHONY: ps
ps: status ## Alias for status

# ============================================================================
# Diagnostics
# ============================================================================

.PHONY: config-check
config-check: ## Validate the rendered Xray config
	@if [ ! -f data/xray/config.json ]; then \
		echo "ERROR: data/xray/config.json not found. Run 'make up' first."; \
		exit 1; \
	fi
	@docker run --rm -v $$(pwd)/data/xray:/etc/xray:ro teddysun/xray \
		xray -test -config /etc/xray/config.json
	@echo "✓ Config is valid."
