# Digital-platform-aggregator-of-IT-vacancies-FSP-

Отраслевой агрегатор ИТ-вакансий с **обратной механикой подбора**: кандидаты автоматически
категоризируются по подтверждённому профилю (данные Федерации спортивного программирования),
а работодатель выбирает категорию и сам выходит на кандидата с вакансией и зарплатой.

> Статус: фаза 1 — ядро бэкенда (аутентификация, модели и миграции, RLS, AccessPolicy, тесты IDOR).
> План: [`docs/PLAN.md`](docs/PLAN.md), архитектура: [`docs/architecture.md`](docs/architecture.md).

## Быстрый старт (локально)
Нужны только Docker (Docker Desktop / colima) и `make`. Python и Node на ПК ставить не нужно.

```bash
make env
make dev
make verify
make test
```

`make env` создаёт .env со случайными секретами, `make dev` собирает и поднимает всё,
`make verify` — смоук-тест (включая регистрацию и вход) и проверка прав БД и RLS,
`make test` — линт и тесты в контейнерах (SQLite и одноразовый PostgreSQL с RLS).
Если порт 8088 занят, поменяйте `HTTP_PORT` в `.env`.

Открыть в браузере: http://localhost:8088 (приложение), http://localhost:8088/api-docs/ (документация API).
Остановить: `make down`; удалить вместе с данными БД: `make clean`.

## Управление сервисами по отдельности
Каждый сервис описан в своём файле `deploy/compose.<service>.yml`, общие настройки — один раз в `deploy/common.yml`.

| Команда | Что делает |
|---|---|
| `make up S="db api"` | поднять только выбранные сервисы |
| `make down S=web` | остановить и удалить сервис (данные сохраняются) |
| `make logs S=api` | логи сервиса |
| `make test` | линт и тесты бэка (SQLite + PostgreSQL с RLS) + сборка фронта в контейнерах |
| `make verify` | смоук-тест работающего стека + проверка прав БД |
| `make migrate` | применить миграции вручную (обычно выполняются сами при старте) |
| `make create-admin EMAIL=...` | создать суперадмина (пароль спросит интерактивно) |
| `make secrets-check` | поиск утёкших секретов (gitleaks) |
| `make prod` | запуск на сервере (80/443, лимиты, автоперезапуск) |

Сервисы: `db` (PostgreSQL), `migrate` (one-shot: миграции и настройка роли приложения),
`api` (FastAPI), `worker` (фоновые задачи), `fsp-mock` (мок API ФСП), `web` (статика React),
`proxy` (Caddy: TLS, заголовки безопасности).

## API (фаза 1)
Полная схема: http://localhost:8088/api-docs/. Префикс `/api/v1`.

| Группа | Эндпоинты |
|---|---|
| `auth` | `POST register/candidate`, `POST register/employer`, `POST login`, `POST refresh`, `POST logout`, `GET me` |
| `candidate` | `GET/PATCH profile` |
| `employer` | `GET company`, `GET/POST vacancies`, `GET/PATCH/DELETE vacancies/{id}`, `POST vacancies/{id}/publish`, `POST vacancies/{id}/close` |
| `admin` | `GET companies?status=`, `POST companies/{id}/status` |
| `public` | `GET skills`, `GET health`, `GET health/ready` |

Access-токен (15 мин) приходит в теле ответа, refresh — в httpOnly-cookie; `refresh`/`logout`
требуют заголовок `X-CSRF-Token` со значением cookie `csrf_token`. Публикация вакансии доступна
после одобрения компании модератором. Первый администратор: `make create-admin EMAIL=...`.

## Структура
```
backend/    FastAPI: api -> services -> repositories -> models
fsp-mock/   мок API ФСП
frontend/   Vite + React + TS (порталы /app, /company, /admin)
deploy/     compose-файлы по сервисам, Caddy
scripts/    служебные скрипты (генерация .env)
docs/       план, архитектура
```

## Деплой на сервер
```bash
git clone <repo> && cd <repo>
make env                                  # затем в .env: SITE_ADDRESS=ваш-домен (APP_ENV=prod задаёт make prod)
make prod                                 # Caddy сам получит TLS-сертификат
```

## Безопасность
- Секреты только в `.env` (генерируются локально, права 600); в репозитории — `.env.example` без значений.
- gitleaks в pre-commit и CI; в prod приложение не стартует со слабыми секретами.
- БД не публикует порты; приложение работает под ролью без прав на DDL; владелец схемы — только для миграций.
- Row Level Security: кандидат видит и меняет только свой профиль, работодатель — вакансии своей компании
  (вторая линия после фильтров репозиториев); журнал аудита только на вставку.
- Пароли — argon2id; refresh-токены хранятся хешами, ротируются атомарно, повторное использование
  отзывает цепочку; лимит попыток входа и по IP, и по аккаунту.
- Каталог кандидатов на уровне БД доступен только одобренным компаниям и без скрытых профилей;
  блокировка компании модератором блокирует и её вакансии.
- Имя и контакты кандидата шифруются в БД (AES-256-GCM, ключ `FIELD_ENCRYPTION_KEY`), шифртекст
  привязан к полю и владельцу.
- В prod каждый сервис проверяет силу только своих секретов и не стартует со слабыми.
- Тесты IDOR перечисляют все эндпоинты автоматически: новый маршрут без проверки прав уронит CI.
- Контейнеры: non-root, read-only FS, `cap_drop: ALL`, `no-new-privileges`, лимиты ресурсов.
- Caddy: HTTPS, HSTS, CSP, X-Frame-Options, лимит тела запроса.

## Команда
3 человека: два разработчика и системный аналитик.
