# Бэкенд

## Слои

```
HTTP-запрос
  └─ api/v1/<router>.py      только HTTP: схемы запроса/ответа, коды, cookie; права — через require()
       └─ services/<x>.py    сценарий: AccessPolicy.ensure, бизнес-правила, аудит, очередь писем, commit
            └─ repositories/  запросы к БД; любой запрос проходит через _scope() — фильтр владельца
                 └─ models/   таблицы SQLAlchemy
PostgreSQL: Row Level Security — вторая линия, если фильтр в коде забыли
```

Правила, которые держат код единообразным:

- **Роутер не принимает решений.** Он разбирает запрос, вызывает сервис и упаковывает ответ.
  Роль проверяется зависимостью `require(Action.X)` до разбора тела: чужая роль получает 403, а не 422.
- **Права — только в `services/access.py`** (`AccessPolicy`, перечисление `Action`). Новое правило —
  новая запись в `_RULES`, а не `if user.role == ...` в коде.
- **Доступ к строкам — только через репозиторий.** `BaseRepository[T]` даёт `get`, `first`, `add`,
  `lock_or_404`, курсорную пагинацию `list_page`; наследник переопределяет `_scope()` (фильтр владельца
  или компании). Поэтому известный чужой `id` возвращает 404.
- **Сервис коммитит сам** и в одной транзакции пишет аудит (`AuditRepository.record`) и письма в очередь
  (`Outbox.enqueue`) — письмо не уйдёт, если действие откатилось.
- **Ошибки — доменные исключения** из `core/errors.py` (`NotFoundError`, `ForbiddenError`, `ConflictError`,
  `InvalidStateError`, `RateLimitedError`, `WrongPasswordError` …). Обработчик превращает их в единый ответ
  `{"error": {"code", "message"}}`; внутренности клиенту не уходят.
- **Конфигурация — только из окружения** (`core/config.py`, pydantic-settings). Секрет читается через
  `settings.secret(name)`: в prod слабое или пустое значение — ошибка запуска.

## Карта модулей

| Путь | Что внутри |
|---|---|
| `app/main.py` | фабрика приложения: роутеры, обработчики ошибок, лимиты, клиенты интеграций в `app.state` |
| `app/cli.py` | служебные команды: `create-admin`, `reset-2fa`, `confirm-email`, `seed-demo` |
| `app/api/deps.py` | DI: сессия БД, `Principal` из access-токена (+ контекст RLS), `require(action)`, клиенты |
| `app/api/v1/*.py` | роутеры: `auth`, `account` (почта, пароль), `candidate`, `profile_import`, `fsp`, `candidate_interviews`, `candidate_offers`, `employer`, `employer_interviews`, `catalog`, `insights`, `admin`, `admin_ai`, `public`, `health` |
| `app/core/` | `config`, `errors`, `security` (argon2, JWT), `crypto` (AES-GCM), `signing` (Ed25519), `totp`, `ratelimit` (+`ratelimit_pg`), `cache` (TTL-кэш), `validation` (русские сообщения), `logging`, `timeutil` |
| `app/db/` | `session` (движок, `set_rls_context`, `system_scope`), `provision` (роль приложения и права), `demo` (демо-данные) |
| `app/models/` | таблицы и перечисления (`enums.py`) |
| `app/repositories/` | `base` + по одному на агрегат: `users`, `candidates`, `companies`, `vacancies`, `catalog`, `offers`, `interviews`, `fsp`, `passports`, `audit`, `admin`, `insights` (агрегаты для радара) |
| `app/services/` | сценарии; подпапки `matching/` (факторы соответствия), `interviews/` (общая часть, сторона компании, сторона кандидата), `resume/` (извлечение текста, правила, ИИ) |
| `app/integrations/` | внешние системы за интерфейсами: `fsp.py` (`FspClient`), `notifier.py` (`Notifier`), `ai/` (`AiClient`, проверка адресов) |
| `app/worker/` | `__main__` (цикл задач), `jobs.py` (задачи) |
| `migrations/` | Alembic; `rls.py` — построители политик RLS |
| `tests/` | pytest: `conftest.py` (приложение, БД, подмены), `helpers.py` и `flows.py` (готовые сценарии), `fake_fsp.py`, `fake_notifier.py` |

### Сервисы по доменам

| Домен | Модули |
|---|---|
| Вход и сессии | `auth.py` (вход, refresh с ротацией, выход, создание администратора), `mfa.py`, `enrollment.py` (коды подключения 2FA) |
| Аккаунт и почта | `account.py` (регистрация без раскрытия занятого адреса, подтверждение, сброс пароля, удаление кандидата), `email_tokens.py`, `emails.py` (шаблоны), `outbox.py` (очередь) |
| Кандидат | `candidates.py` (профиль), `profile_import.py` (черновик из ФСП и резюме), `resume/` |
| ФСП | `fsp.py` (привязка кодом), `fsp_sync.py` (достижения), `categorization.py` (категории, Strategy `CategoryRule`), `passport.py` (паспорт навыков) |
| Работодатель | `employer.py` (компания, вакансии), `catalog.py` (каталог, сортировка по соответствию с кэшем), `matching/` |
| Найм | `interviews/`, `offers.py` (оффер, раскрытие контактов) |
| Аналитика | `insights.py` (радар зарплат, путь роста, k-анонимность) |
| Модерация | `admin.py`, `moderation.py`, `ai_providers.py` |
| Общее | `access.py` (AccessPolicy), `common.py` (применение полей, навыки), `directory.py`, `skill_matching.py` (синонимы навыков) |

## Путь запроса (пример: принять оффер)

1. `POST /api/v1/candidate/offers/{id}/accept` → `api/v1/candidate_offers.py`.
2. `get_principal` проверяет access-токен, загружает пользователя, задаёт контекст RLS
   (`app.user_id`, `app.role`) — дальше PostgreSQL сам не покажет чужие офферы.
3. `CandidateOfferService` при создании вызывает `policy.ensure(principal, Action.OFFER_RESPOND)`;
   `accept` берёт профиль и оффер через репозитории с блокировкой строк (`own_or_404(for_update=True)`,
   `lock_or_404`) и проверяет статус и срок.
4. Шифрует снимок имени и контактов кандидата с привязкой к офферу, пишет аудит, ставит письмо
   компании в очередь — всё в одной транзакции, `commit`.
5. Worker через несколько секунд отправляет письмо (`OutboxJob`).

## Как добавить эндпоинт

1. **Схемы** в `app/schemas/<домен>.py`: `...In` для запроса (ограничения длины и значений),
   `...Out` для ответа (`ORMModel` для чтения из моделей).
2. **Право**: если нужно новое — значение в `Action` и правило в `_RULES` (`services/access.py`).
3. **Репозиторий**: запрос с учётом `_scope()`; новый агрегат — наследник `BaseRepository` со своим `_scope`.
4. **Сервис**: `policy.ensure(...)` → правила → аудит → `commit`. Ошибки — исключения из `core/errors.py`.
5. **Роутер**: `@router.get(..., dependencies=[require(Action.X)], summary="...")`; `summary` попадает
   в OpenAPI и в документацию `/api-docs/`.
6. **Лимит** (вход, письма, перебор кодов): `await check_rate_limit(request, "<scope>", key=...)`,
   значение — в `Settings` и в словаре `rate_limits` в `main.py`.
7. **Тесты** в `backend/tests/test_<домен>.py`: успешный сценарий, чужая роль, чужая строка (IDOR),
   неверное состояние. `test_idor.py` сам перебирает все маршруты: новый маршрут без авторизации уронит CI.
   Если маршрут намеренно публичный — добавьте префикс в `PUBLIC_PREFIXES` с комментарием, чем он защищён.
8. **Фронт**: `npm run gen:api` при запущенном стеке, тип в `src/api/types.ts`, функция в `src/api/endpoints.ts`.

## Как добавить таблицу

1. Модель в `app/models/`, экспорт в `app/models/__init__.py`.
2. Миграция: `backend/migrations/versions/00NN_<что>.py` (ручная, с `downgrade`). Для данных пользователей —
   сразу RLS: `enable(table)` и политики из `migrations/rls.py` (`owns_profile`, `member_of`, `PRIVILEGED`).
3. Права роли приложения выдаются автоматически (`ALTER DEFAULT PRIVILEGES` в `db/provision.py`);
   особые случаи (только вставка, как у аудита) — там же.
4. Тест RLS в `tests/test_rls_postgres.py`: прямым SQL под ролью приложения убедиться, что чужие строки
   не видны и не меняются.
5. В PostgreSQL-тестах таблицы очищаются между тестами — добавьте новую в `_TRUNCATE` в `tests/dbsetup.py`.

## Как добавить фактор подбора или правило категории

- Фактор соответствия: класс-наследник `Factor` в `services/matching/factors.py` (`key`, `label`, `weight`,
  метод `score` возвращает долю 0..1 и объяснение), добавить в кортеж `FACTORS`. Итог нормируется
  по сумме весов, фронт покажет новый фактор в «Почему» без изменений.
- Правило категории ФСП: наследник `CategoryRule` в `services/categorization.py`, добавить в `RULES`.

## Как добавить фоновую задачу

Класс-наследник `Job` в `app/worker/jobs.py` (`name`, `interval_seconds`, `async run()`), регистрация
в `build_jobs`. Задача должна быть идемпотентной и безопасной при нескольких экземплярах worker:
захват работы — `FOR UPDATE SKIP LOCKED` (пример — `claim_due_links` в `repositories/fsp.py`).

## Тесты

- `make test-backend` — ruff, затем pytest дважды: на SQLite (быстро, без RLS) и на одноразовом
  PostgreSQL с RLS и ролями (`scripts/test-backend.sh`). Порог покрытия — 80 % (сейчас ~95 %).
- Внешние системы подменены: `FakeFspClient`, `MemoryNotifier`, `httpx.MockTransport` для моделей ИИ.
- Готовые сценарии в `tests/flows.py`: `approved_employer`, `verified_candidate`, `send` (приглашение →
  собеседование → оффер) — используйте их, а не собирайте шаги заново.
- Тестовые пароли берутся из `tests/helpers.PASSWORD` (случайный на прогон): литералы паролей
  в тестах ловит gitleaks.
