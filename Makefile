.PHONY: help up down restart logs status install init add remove list backup

help:
	@echo "TryKuhn VPN — команды:"
	@echo "  make install        — подготовить сервер (ufw, docker)"
	@echo "  make init           — сгенерировать ключи и конфиг при первом запуске"
	@echo "  make up             — запустить VPN"
	@echo "  make down           — остановить VPN"
	@echo "  make restart        — перезапустить"
	@echo "  make logs           — посмотреть логи Xray"
	@echo "  make status         — статус сервисов"
	@echo "  make add USER=name  — добавить пользователя"
	@echo "  make remove USER=name — удалить пользователя"
	@echo "  make list           — список пользователей"
	@echo "  make show USER=name — показать ссылку и QR"
	@echo "  make backup         — бэкап users.json и config"

install:
	@bash scripts/install.sh

init:
	@bash scripts/generate-keys.sh

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart xray

logs:
	docker compose logs -f xray

status:
	docker compose ps

add:
	@docker compose exec manager vpn-user add $(USER)

add-list:
	@docker compose exec manager vpn-user add-many --prefix $(PREFIX) --count $(COUNT)

add-file:
	@docker compose exec manager vpn-user add-from-file --file $(FILE)

remove:
	@docker compose exec manager vpn-user remove $(USER)

list:
	@docker compose exec manager vpn-user list

show:
	@docker compose exec manager vpn-user show $(USER)

backup:
	@bash scripts/backup.sh