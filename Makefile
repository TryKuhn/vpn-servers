SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
COMPOSE := docker compose
CLI := $(COMPOSE) run --rm manager python -m manager.cli
ALEMBIC := $(COMPOSE) run --rm manager alembic
.PHONY: help install init certs build db.up migrate migrate.upgrade migrate.downgrade migrate.revision render validate validate.rendered predeploy up up.fast down restart status health logs logs-manager logs-xray add-user remove-user disable-user enable-user list-users show-user rotate-token import-legacy sync backup restore deploy-from-scratch shell-manager
help:
	@printf "\033[0;36mvpn-servers v0.1 async\033[0m — operator commands\n\n"
	@printf "\033[0;32mSetup:\033[0m\n  make install                 — bootstrap fresh Ubuntu server: docker, ufw, tools\n  make init                    — create/update .env with Reality keys and random passwords\n  make certs                   — issue certs/fullchain.pem and certs/privkey.pem via standalone certbot\n  make deploy-from-scratch     — build, migrate, render, validate, start, backup\n\n"
	@printf "\033[0;32mMigrations:\033[0m\n  make migrate                 — alias for migrate.upgrade\n  make migrate.upgrade         — alembic upgrade head\n  make migrate.downgrade       — alembic downgrade -1\n  make migrate.revision MSG=x  — alembic revision --autogenerate\n\n"
	@printf "\033[0;32mUsers:\033[0m\n  make add-user NAME=name      — add user with default device\n  make remove-user NAME=name   — remove user\n  make disable-user NAME=name  — disable user\n  make enable-user NAME=name   — enable user\n  make list-users              — list users\n  make show-user NAME=name     — show subscription and credentials\n  make rotate-token NAME=name  — rotate default device subscription token\n  make import-legacy FILE=f    — import legacy CSV\n  make sync                    — render configs and restart protocol services\n\n"
install:
	sudo ./scripts/install.sh
init:
	./scripts/generate-keys.sh
certs:
	./scripts/issue-certs-standalone.sh
build:
	$(COMPOSE) build
db.up:
	$(COMPOSE) up -d postgres
migrate: migrate.upgrade
migrate.upgrade: db.up
	$(ALEMBIC) upgrade head
migrate.downgrade: db.up
	$(ALEMBIC) downgrade -1
migrate.revision: db.up
	@test -n "$(MSG)" || (echo "Usage: make migrate.revision MSG='message'" && exit 1)
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"
render: migrate.upgrade
	$(CLI) render-configs
validate: render validate.rendered
validate.rendered:
	./scripts/validate-configs.sh
predeploy:
	$(COMPOSE) build manager naive
	$(MAKE) migrate.upgrade
	$(MAKE) render
	$(MAKE) validate.rendered
up: predeploy
	$(COMPOSE) up -d --build --remove-orphans
up.fast:
	$(COMPOSE) up -d --build --remove-orphans
down:
	$(COMPOSE) down
restart:
	$(COMPOSE) restart
status:
	$(COMPOSE) ps
health:
	curl -fsS http://127.0.0.1:$${MANAGER_PORT:-8080}/health && echo
logs:
	$(COMPOSE) logs -f --tail=200
logs-manager:
	$(COMPOSE) logs -f --tail=200 manager
logs-xray:
	$(COMPOSE) logs -f --tail=200 xray
add-user:
	@test -n "$(NAME)" || (echo "Usage: make add-user NAME=MrNykterstein-PC" && exit 1)
	$(CLI) add-user "$(NAME)"
	$(MAKE) sync
remove-user:
	@test -n "$(NAME)" || (echo "Usage: make remove-user NAME=MrNykterstein-PC" && exit 1)
	$(CLI) remove-user "$(NAME)"
	$(MAKE) sync
disable-user:
	@test -n "$(NAME)" || (echo "Usage: make disable-user NAME=MrNykterstein-PC" && exit 1)
	$(CLI) disable-user "$(NAME)"
	$(MAKE) sync
enable-user:
	@test -n "$(NAME)" || (echo "Usage: make enable-user NAME=MrNykterstein-PC" && exit 1)
	$(CLI) enable-user "$(NAME)"
	$(MAKE) sync
list-users:
	$(CLI) list-users
show-user:
	@test -n "$(NAME)" || (echo "Usage: make show-user NAME=MrNykterstein-PC" && exit 1)
	$(CLI) show-user "$(NAME)"
rotate-token:
	@test -n "$(NAME)" || (echo "Usage: make rotate-token NAME=MrNykterstein-PC" && exit 1)
	$(CLI) rotate-token "$(NAME)"
	$(MAKE) sync
import-legacy:
	@test -n "$(FILE)" || (echo "Usage: make import-legacy FILE=legacy_users.csv" && exit 1)
	$(CLI) import-legacy "$(FILE)"
	$(MAKE) sync
sync: render validate.rendered
	$(COMPOSE) up -d --build xray hysteria naive haproxy
backup:
	./scripts/backup.sh
restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/archive.tar.gz" && exit 1)
	./scripts/restore-backup.sh "$(FILE)"
deploy-from-scratch: build migrate.upgrade render validate.rendered up backup
shell-manager:
	$(COMPOSE) run --rm manager bash
