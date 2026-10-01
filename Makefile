# Управление сервисами по отдельности:
#   make up S="db api"     поднять только выбранные (зависимости compose подтянет сам)
#   make down S=web        остановить сервис
#   make logs S=api        логи
#   make dev               всё локально (http://localhost:8088, порт: HTTP_PORT в .env)
#   make prod              всё на сервере
SHELL := /bin/sh
ALL   := db migrate api worker fsp-mock web proxy
S     ?= $(ALL)
MODE  ?= dev
COMPOSE_FILES = -f deploy/compose.base.yml $(foreach s,$(ALL),-f deploy/compose.$(s).yml) -f deploy/compose.$(MODE).yml
DC = docker compose --env-file .env $(COMPOSE_FILES)

.PHONY: env up down stop logs logs-dump ps build dev prod test test-backend test-fsp-mock test-frontend smoke check-db verify config secrets-check clean migrate create-admin reset-admin-2fa check-dupes seed-demo load

env:            ## создать .env со случайными секретами
	@./scripts/gen-env.sh

up: env check-dupes  ## поднять сервисы S
	$(DC) up -d --build $(S)
	@# Caddyfile смонтирован в контейнер: перезапуск подхватывает его изменения (admin API выключен)
	@case " $(S) " in *" proxy "*) $(DC) restart proxy >/dev/null ;; esac

down:           ## остановить и удалить сервисы S (тома сохраняются)
	$(DC) rm -sf $(S)

stop:
	$(DC) stop $(S)

logs:
	$(DC) logs -f --tail=100 $(S)

logs-dump:      ## логи всех сервисов без -f (для CI)
	$(DC) logs --no-color --tail=200

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

test: test-backend test-fsp-mock test-frontend

test-backend:   ## линт + тесты в контейнерах: SQLite и одноразовый PostgreSQL с RLS
	./scripts/test-backend.sh

test-fsp-mock:  ## линт и тесты мока ФСП в контейнере
	docker run --rm -v "$$PWD/fsp-mock:/src:ro" -w /src -e PYTHONDONTWRITEBYTECODE=1 python:3.12-slim \
	  sh -c "pip install -q --disable-pip-version-check -r requirements-dev.txt && ruff check --no-cache . && pytest -q -p no:cacheprovider"

test-frontend:  ## тесты и сборка фронта в контейнере (node_modules на ПК не появляются)
	docker build -q --target build -t itmatch/web:build frontend

HTTP_PORT ?= $(or $(shell grep -s '^HTTP_PORT=' .env | cut -d= -f2),8088)
MAIL_UI_PORT ?= $(or $(shell grep -s '^MAIL_UI_PORT=' .env | cut -d= -f2),8025)

smoke:          ## смоук-тест работающего стека
	MAIL_URL=http://localhost:$(MAIL_UI_PORT) ./scripts/smoke.sh http://localhost:$(HTTP_PORT)

check-db:       ## проверка прав роли приложения в работающей БД
	@DC="$(DC)" ./scripts/check-db.sh

verify: smoke check-db  ## всё сразу после make dev

migrate:        ## применить миграции вручную (обычно выполняются сами при make dev/prod)
	$(DC) run --rm migrate

create-admin:   ## создать суперадмина: make create-admin EMAIL=admin@example.org (пароль спросит)
	@test -n "$(EMAIL)" || { echo "укажите EMAIL=..."; exit 1; }
	$(DC) exec api python -m app.cli create-admin --email "$(EMAIL)" --superadmin

load:           ## нагрузочный тест (k6): make load EMP=<токен работодателя> CAND=<токен кандидата> VAC=<id вакансии>
	@test -n "$(EMP)" -a -n "$(CAND)" -a -n "$(VAC)" || { echo "укажите EMP, CAND и VAC"; exit 1; }
	docker run --rm --network itmatch_edge -v "$$PWD/scripts/load:/load:ro" \
	  -e EMP="$(EMP)" -e CAND="$(CAND)" -e VAC="$(VAC)" grafana/k6:2.3.0 run --quiet /load/catalog.js

seed-demo:      ## демо-кандидаты для каталога (только dev): make seed-demo N=500
	$(DC) exec api python -m app.cli seed-demo --candidates "$(or $(N),500)"

check-dupes:    ## копии файлов от iCloud/Finder ("file 2.py") ломают сборку — проверяем заранее
	@./scripts/check-dupes.sh

reset-admin-2fa: ## сбросить 2FA администратора (потерян телефон): make reset-admin-2fa EMAIL=...
	@test -n "$(EMAIL)" || { echo "укажите EMAIL=..."; exit 1; }
	$(DC) exec api python -m app.cli reset-2fa --email "$(EMAIL)"

secrets-check:  ## поиск утёкших секретов в файлах и истории git
	docker run --rm -v "$$PWD:/repo" zricethezav/gitleaks:latest git /repo --no-banner

clean:          ## ОСТОРОЖНО: удаляет контейнеры и тома (данные БД)
	$(DC) down -v
