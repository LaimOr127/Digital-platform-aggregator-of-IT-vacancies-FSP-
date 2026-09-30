# Управление сервисами по отдельности:
#   make up S="db api"     поднять только выбранные (зависимости compose подтянет сам)
#   make down S=web        остановить сервис
#   make logs S=api        логи
#   make dev               всё локально (http://localhost:8080)
#   make prod              всё на сервере
SHELL := /bin/sh
ALL   := db api worker fsp-mock web proxy
S     ?= $(ALL)
MODE  ?= dev
COMPOSE_FILES = -f deploy/compose.base.yml $(foreach s,$(ALL),-f deploy/compose.$(s).yml) -f deploy/compose.$(MODE).yml
DC = docker compose --env-file .env $(COMPOSE_FILES)

.PHONY: env up down stop logs ps build dev prod test test-backend test-frontend config secrets-check clean

env:            ## создать .env со случайными секретами
	@./scripts/gen-env.sh

up: env         ## поднять сервисы S
	$(DC) up -d --build $(S)

down:           ## остановить и удалить сервисы S (тома сохраняются)
	$(DC) rm -sf $(S)

stop:
	$(DC) stop $(S)

logs:
	$(DC) logs -f --tail=100 $(S)

ps:
	$(DC) ps

build:
	$(DC) build $(S)

config:         ## проверить итоговую конфигурацию compose
	$(DC) config -q && echo "compose OK"

dev:
	$(MAKE) up MODE=dev

prod:
	$(MAKE) up MODE=prod

test: test-backend test-frontend

test-backend:   ## линт + тесты в изолированном контейнере (ничего не ставится на ПК)
	docker build -q --target test -t itmatch/api:test backend && docker run --rm itmatch/api:test

test-frontend:
	docker run --rm -v "$$PWD/frontend:/app" -w /app node:22-alpine sh -c "npm ci --no-audit --no-fund && npm run build"

secrets-check:  ## поиск утёкших секретов в файлах и истории git
	docker run --rm -v "$$PWD:/repo" zricethezav/gitleaks:latest git /repo --no-banner

clean:          ## ОСТОРОЖНО: удаляет контейнеры и тома (данные БД)
	$(DC) down -v
