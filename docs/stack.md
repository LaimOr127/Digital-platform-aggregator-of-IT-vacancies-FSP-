# Технологии: на чём что написано и почему

Главный принцип из плана — один язык на бэке (Python), один на фронте (TypeScript), минимум
инфраструктуры. PostgreSQL закрывает то, для чего обычно берут Redis, брокер очередей и поиск.

## Сервисы

| Сервис | Технологии | Образ | Назначение |
|---|---|---|---|
| `api` | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 (async, asyncpg), Pydantic v2 | `python:3.12-slim`, non-root | REST API `/api/v1` |
| `worker` | тот же код, что `api` (`python -m app.worker`) | тот же образ | фоновые задачи: синхронизация ФСП, письма, истечение офферов, очистка лимитов |
| `migrate` | Alembic + `app.db.provision` | тот же образ | one-shot: миграции и права роли приложения |
| `db` | PostgreSQL 16 | `postgres:16-alpine` | данные, RLS, лимиты запросов, очередь писем |
| `web` | Vite + React 19 + TypeScript, собранная статика | multi-stage: node для сборки, Caddy для раздачи | SPA |
| `proxy` | Caddy 2 | `caddy:2-alpine` | HTTPS (Let's Encrypt), заголовки безопасности, маршрутизация |
| `fsp-mock` | FastAPI | `python:3.12-slim` | мок API ФСП для разработки и демо |
| `mailpit` | Mailpit | только dev | ловит все письма, UI на `:8025` |

## Бэкенд

| Задача | Библиотека | Почему |
|---|---|---|
| HTTP и OpenAPI | FastAPI | типы → валидация → OpenAPI-схема → типы фронта; DI через `Depends` удобно подменять в тестах |
| Валидация | Pydantic v2 | одна схема и для запроса, и для документации; сообщения переведены (`core/validation.py`) |
| ORM | SQLAlchemy 2 async | явные запросы, без магии; один и тот же код на PostgreSQL и SQLite (быстрые тесты) |
| Миграции | Alembic | версии схемы и RLS-политик в git, применяет отдельная роль-владелец |
| Пароли | argon2-cffi (argon2id) | рекомендация OWASP; хеш считается в потоке (`asyncio.to_thread`), чтобы не блокировать цикл событий |
| Токены | PyJWT | короткий access JWT; refresh — случайная строка, в БД только хеш |
| Шифрование полей | cryptography (AES-256-GCM) | имя и контакты кандидата, ключи ИИ, секрет TOTP; шифртекст привязан к полю и владельцу |
| Подпись паспорта | cryptography (Ed25519) | проверяется кем угодно по публичному ключу |
| 2FA | собственная реализация TOTP (RFC 6238, `core/totp.py`) | ~50 строк вместо зависимости, покрыто тестами по векторам RFC |
| HTTP-клиент | httpx | ФСП и языковые модели; `MockTransport` в тестах |
| Резюме | pypdf; DOCX — стандартный `zipfile` | текстовый слой PDF и DOCX; без OCR и без тяжёлых моделей |
| Почта | smtplib в потоке | достаточно для очереди с повторами; канал за интерфейсом `Notifier` |
| Линт | ruff (lint + format) | один быстрый инструмент |
| Тесты | pytest, pytest-asyncio, httpx, pytest-cov | SQLite в памяти для скорости + одноразовый PostgreSQL для RLS |

Почему не Redis/Celery: лимиты запросов, очередь писем и блокировки синхронизации работают на
PostgreSQL (`UNLOGGED`-таблица, `FOR UPDATE SKIP LOCKED`). Меньше сервисов — меньше памяти на сервере
1–2 ГБ и меньше точек отказа. Если нагрузка вырастет, Redis подключается заменой реализации `Limiter`.

Почему без тяжёлых ML-моделей: решение должно работать на недорогом сервере без GPU. Где модель
уместна, она есть, но лёгкая и объяснимая: уровень кандидата оценивается психометрической моделью IRT
(3PL, EAP — [assessment.md](assessment.md)), соответствие вакансии — взвешенными факторами с объяснением
каждого ([matching.md](matching.md)), резюме разбирается правилами или любой подключённой языковой
моделью с согласия кандидата. Качество проверяется процедурой оценки ([validation.md](validation.md)).

## Фронтенд

| Задача | Библиотека | Почему |
|---|---|---|
| Сборка | Vite 7 | быстрый dev-сервер, простая конфигурация |
| UI | React 19 + TypeScript (strict) | типы API генерируются из OpenAPI (`openapi-typescript`) |
| Данные с сервера | TanStack Query 5 | кэш, повторы, курсорная пагинация (`useInfiniteQuery`) |
| Маршруты | React Router 8 | три портала грузятся лениво |
| Формы | react-hook-form + zod 4 | те же правила, что на бэке; ошибки сервера раскладываются по полям |
| Стили | Tailwind CSS 4 | цвета — токены в `src/styles.css`, брендбук ФСП меняется в одном месте |
| Анимации | Motion | только transform/opacity, учитывается `prefers-reduced-motion` |
| Иконки | lucide-react | одна библиотека |
| QR | qrcode | QR-код паспорта навыков |
| Тесты | Vitest + Testing Library + jsdom | компонентные тесты с подменой `fetch` |

Графики (радар зарплат) нарисованы обычными HTML/CSS-блоками (`features/insights/RangeChart.tsx`),
без библиотеки графиков: нужен один тип графика, а библиотека добавила бы сотни КБ.

## Версии библиотек и компонентов

Бэкенд закреплён точными версиями (`backend/requirements*.txt`), фронтенд — `package-lock.json`.

| Компонент | Версия | Лицензия |
|---|---|---|
| Python | 3.12 (`python:3.12-slim`) | PSF |
| FastAPI | 0.142.2 | MIT |
| Uvicorn | 0.54.0 | BSD-3 |
| Pydantic Settings / email-validator | 2.15.0 / 2.3.0 | MIT / Unlicense |
| SQLAlchemy (asyncio) | 2.1.1 | MIT |
| asyncpg | 0.31.0 | Apache-2.0 |
| Alembic | 1.20.0 | MIT |
| argon2-cffi | 25.1.0 | MIT |
| PyJWT | 2.15.1 | MIT |
| cryptography | 50.0.2 | Apache-2.0 / BSD |
| httpx | 0.28.1 | BSD-3 |
| pypdf | 6.19.0 | BSD-3 |
| python-multipart | 0.0.32 | Apache-2.0 |
| pytest / pytest-asyncio / pytest-cov / aiosqlite | 9.1.1 / 1.4.0 / 7.1.0 / 0.22.1 | MIT / Apache-2.0 / MIT / MIT |
| ruff | 0.16.9 | MIT |
| PostgreSQL | 16 (`postgres:16-alpine`) | PostgreSQL License |
| Caddy | 2 (`caddy:2-alpine`) | Apache-2.0 |
| Mailpit (только dev) | 1.27 | MIT |
| React / React DOM | 19.3.0 | MIT |
| TypeScript | 5.9.3 | Apache-2.0 |
| Vite | 7.3.6 | MIT |
| TanStack Query | 5.104.0 | MIT |
| React Router | 8.4.0 | MIT |
| react-hook-form / @hookform/resolvers | 7.89.0 / 5.9.1 | MIT |
| zod | 4.6.5 | MIT |
| Tailwind CSS | 4.3.3 | MIT |
| Motion | 13.4.6 | MIT |
| lucide-react | 1.49.0 | ISC |
| qrcode | 1.5.4 | MIT |
| Inter (шрифт, @fontsource-variable) | 5.3 | OFL-1.1 |
| openapi-typescript / swagger-ui-dist | 7.13.0 / 5.33.0 | MIT / Apache-2.0 |
| Vitest / Testing Library React / jsdom | 5.0.3 / 16.3.3 / 30.1.1 | MIT |
| k6 (нагрузочный тест) | 2.3.0 | AGPL-3.0, отдельный инструмент, не входит в продукт |

Код проекта открыт под лицензией MIT (`LICENSE`).

## Инфраструктура

- **Docker Compose**: отдельный файл на сервис (`deploy/compose.<service>.yml`), общие настройки — один раз
  в `deploy/common.yml` (`extends`), режимы — `compose.dev.yml` и `compose.prod.yml`. Makefile собирает
  нужную комбинацию: `make up S="db api"`.
- **Caddy**: автоматический TLS, HSTS, CSP, лимит тела запроса; admin API выключен.
- **Сети**: `public` (только proxy), `edge` (proxy ↔ web/api), `internal` (api/worker ↔ db/fsp-mock),
  `egress` (только prod: api/worker → реальный API ФСП и SMTP). `edge` и `internal` без выхода в интернет.
- **CI**: GitHub Actions — gitleaks по истории, ruff + pytest (SQLite и PostgreSQL), pip-audit,
  Vitest с покрытием, сборка, npm audit, сквозной прогон стека (`make verify`).
- **Нагрузка**: k6 (`scripts/load/catalog.js`, `make load`).
