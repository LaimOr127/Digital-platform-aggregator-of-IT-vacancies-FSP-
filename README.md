# Digital-platform-aggregator-of-IT-vacancies-FSP-

Отраслевой агрегатор ИТ-вакансий с **обратной механикой подбора**: кандидаты автоматически
категоризируются по подтверждённому профилю (данные Федерации спортивного программирования),
а работодатель выбирает категорию и сам выходит на кандидата с вакансией и зарплатой.

> Статус: фаза 0 — каркас (инфраструктура, CI, health-эндпоинты). План: [`docs/PLAN.md`](docs/PLAN.md),
> архитектура: [`docs/architecture.md`](docs/architecture.md).

## Быстрый старт (локально)
Нужны только Docker (Docker Desktop / colima) и `make`. Python и Node на ПК ставить не нужно.

```bash
make env     # создаёт .env со случайными секретами (права 600, в git не попадает)
make dev     # собирает и поднимает всё: http://localhost:8080
make ps      # статус контейнеров
```

Проверка: `curl localhost:8080/api/v1/health` → `{"status":"ok"}`, документация API — `/api/docs`.

## Управление сервисами по отдельности
Каждый сервис описан в своём файле `deploy/compose.<service>.yml`, общие настройки — один раз в `deploy/common.yml`.

| Команда | Что делает |
|---|---|
| `make up S="db api"` | поднять только выбранные сервисы |
| `make down S=web` | остановить и удалить сервис (данные сохраняются) |
| `make logs S=api` | логи сервиса |
| `make test` | линт и тесты бэка + сборка фронта в контейнерах |
| `make secrets-check` | поиск утёкших секретов (gitleaks) |
| `make prod` | запуск на сервере (80/443, лимиты, автоперезапуск) |

Сервисы: `db` (PostgreSQL), `api` (FastAPI), `worker` (фоновые задачи), `fsp-mock` (мок API ФСП),
`web` (статика React), `proxy` (Caddy: TLS, заголовки безопасности).

## Структура
```
backend/    FastAPI: api -> services -> repositories -> models
fsp-mock/   мок API ФСП
frontend/   Vite + React + TS (порталы /app, /company, /admin)
deploy/     compose-файлы по сервисам, Caddy, init-скрипты БД
scripts/    служебные скрипты (генерация .env)
docs/       план, архитектура
```

## Деплой на сервер
```bash
git clone <repo> && cd <repo>
make env                                  # затем в .env: APP_ENV=prod, SITE_ADDRESS=ваш-домен
make prod                                 # Caddy сам получит TLS-сертификат
```

## Безопасность
- Секреты только в `.env` (генерируются локально, права 600); в репозитории — `.env.example` без значений.
- gitleaks в pre-commit и CI; в prod приложение не стартует со слабыми секретами.
- БД не публикует порты; приложение работает под ролью без прав на DDL; владелец схемы — только для миграций.
- Контейнеры: non-root, read-only FS, `cap_drop: ALL`, `no-new-privileges`, лимиты ресурсов.
- Caddy: HTTPS, HSTS, CSP, X-Frame-Options, лимит тела запроса.

## Команда
3 человека: два разработчика и системный аналитик.
