# Эксплуатация: запуск, деплой, стенд, проблемы

Нужны только Docker и `make`. Python и Node на машине не нужны: тесты и сборка идут в контейнерах.

## Локально

```bash
make env       # .env со случайными секретами (повторный запуск дописывает только новые ключи)
make dev       # сборка и запуск всего стека: http://localhost:8088
make verify    # смоук-тест + проверка прав БД
make test      # линт и тесты: бэкенд (SQLite + PostgreSQL), мок ФСП, фронтенд
```

| Адрес | Что |
|---|---|
| http://localhost:8088 | приложение |
| http://localhost:8088/api-docs/ | документация API (Swagger UI) |
| http://localhost:8025 | Mailpit — все письма приложения |

Демо-данные: `make seed-demo N=2000 C=8` — 2000 анонимных кандидатов и 8 компаний с вакансиями
(для каталога и радара зарплат). **Войти в демо-аккаунты нельзя** — у них нет пароля и почты.
Для входа зарегистрируйте своего пользователя (письмо придёт в Mailpit).

## Команды make

| Команда | Что делает |
|---|---|
| `make up S="db api"` / `make down S=web` / `make logs S=api` / `make ps` | управление выбранными сервисами |
| `make dev` / `make prod` | весь стек в режиме dev / prod |
| `make migrate` | применить миграции вручную (обычно применяются сами) |
| `make create-admin EMAIL=…` | суперадмин; пароль спросит, выведет одноразовый код подключения 2FA |
| `make reset-admin-2fa EMAIL=…` | потерян телефон: новая настройка 2FA, все сессии администратора завершаются |
| `make confirm-email EMAIL=…` | подтвердить почту пользователя вручную (письмо не дошло) |
| `make seed-demo N=… C=…` | демо-кандидаты и компании (не работает в prod) |
| `make load EMP=… CAND=… VAC=…` | нагрузочный тест k6 (токены работодателя и кандидата, id вакансии) |
| `make evaluate ARGS="--seed 7"` | процедура оценки тестирования и подбора на синтетике, отчёт в Markdown ([validation.md](validation.md)) |
| `make docs-docx` | единый DOCX сопроводительной документации со схемами (`docs/build/itmatch-docs.docx`) |
| `make test`, `make test-backend`, `make test-frontend`, `make test-fsp-mock` | тесты |
| `make smoke`, `make check-db`, `make verify` | проверки работающего стека |
| `make secrets-check` | gitleaks по файлам и истории |
| `make check-dupes` | копии файлов от iCloud (`file 2.py`) |
| `make config` | проверить итоговую конфигурацию compose |
| `make clean` | **удаляет контейнеры и тома с данными БД** |

## Деплой на сервер

Сервер: 1–2 vCPU, 2 ГБ RAM, Docker, открытые порты 80 и 443, DNS домена указывает на сервер.

```bash
git clone <repo> && cd <repo>
make env
# в .env: SITE_ADDRESS=ваш-домен, PUBLIC_URL=https://ваш-домен, SMTP_* (см. ниже)
make prod                                 # Caddy сам получит TLS-сертификат
make create-admin EMAIL=admin@ваш-домен
```

В prod: `APP_ENV=prod` задаётся compose-файлом, слабые секреты не дают стартовать, Mailpit не запускается,
демо-коды ФСП выключены (для демо-стенда с моком — `FSP_DEMO_CODES_PROD=true`), api работает
в `API_WORKERS` процессах, у контейнеров лимиты памяти и автоперезапуск.

Обновление: `git pull && make prod` (миграции применятся сами). Бэкап БД:

```bash
docker compose -p itmatch exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc itmatch' > backup-$(date +%F).dump
```

## Переменные окружения

Полный список с комментариями — `.env.example`. Секреты генерирует `make env`; в репозиторий `.env`
не попадает.

| Группа | Переменные |
|---|---|
| Режим | `APP_ENV` (dev/prod), `LOG_LEVEL`, `COMPANY_PREMODERATION` (по умолчанию `false`: компания после регистрации одобрена сразу, модерация — постфактум) |
| БД | `DB_NAME`, `DB_OWNER_USER`/`DB_OWNER_PASSWORD` (только migrate), `APP_DB_USER`/`APP_DB_PASSWORD`, `DB_POOL_SIZE` |
| Секреты приложения | `JWT_SECRET`, `FIELD_ENCRYPTION_KEY` (AES), `PASSPORT_SIGNING_KEY` (Ed25519), `FSP_API_KEY` |
| ФСП | `FSP_BASE_URL`, `FSP_DEMO_CODES` (dev), `FSP_DEMO_CODES_PROD` (демо-стенд) |
| ИИ | `ANTHROPIC_API_KEY`, `AI_MODEL` (запасной вариант; основное — в админке), `AI_ALLOW_HTTP`, `AI_ALLOW_PRIVATE_NETWORK` |
| Почта | `PUBLIC_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `MAIL_UI_PORT` (dev) |
| Сеть | `SITE_ADDRESS` (домен для Caddy), `HTTP_PORT` (локальный порт) |
| Производительность | `API_WORKERS`, `DB_POOL_SIZE` |
| Лимиты | значения по умолчанию — в `backend/app/core/config.py` (формат `10/minute`, `3/hour`, `50/day`). Чтобы менять их через `.env`, добавьте переменную (например, `AUTH_RATE_LIMIT`) в `environment` шаблона `python-app` в `deploy/common.yml` — контейнеры получают только явно перечисленные переменные |

## Тестовый стенд без почты

Если на сервере не настроен SMTP, письма с подтверждением не доходят — войти после регистрации нельзя.
Два выхода:

1. **Правильный**: настроить SMTP (`docs/integrations.md`, раздел «Настройка SMTP на стенде»).
2. **Быстрый**: тестировщик регистрируется на сайте как обычно, оператор на сервере подтверждает адрес:
   ```bash
   make confirm-email EMAIL=tester@example.org
   ```
   Пароль оператор не узнаёт; действие записывается в аудит (`auth.email_confirmed_by_operator`).
   Компании после этого ещё нужно одобрение модератора в `/admin`.

## Типовые проблемы

| Симптом | Причина и решение |
|---|---|
| Письмо не пришло | dev — смотрите Mailpit `:8025`; сервер — нет SMTP (см. выше); лимит 3 письма в час на адрес |
| `429` при входе или в смоук-тесте | сработал лимит (общий для процессов, хранится в БД и переживает перезапуск). Сброс в dev: `docker exec itmatch-db-1 sh -c 'psql -U "$POSTGRES_USER" -d itmatch -c "TRUNCATE rate_limit_buckets"'` |
| `make dev` останавливается на check-dupes | проект в iCloud/OneDrive создал копии `file 2.py`; удалите их (`make check-dupes` покажет) или перенесите проект |
| Docker: `Resource deadlock avoided` при сборке | iCloud выгрузил файлы из папки; материализуйте их (`find backend frontend -type f -exec cat {} + > /dev/null`) или перенесите проект |
| Порт 8088 занят | `HTTP_PORT` в `.env` |
| Администратор потерял телефон | `make reset-admin-2fa EMAIL=…` |
| Радар зарплат «мало данных» | группы меньше 5 значений не показываются (k-анонимность); для демо — `make seed-demo` |
| Паспорта перестали проверяться | сменили `PASSPORT_SIGNING_KEY` — перевыпустите паспорта |

## Наблюдаемость

- `GET /api/v1/health` (процесс жив) и `/health/ready` (есть связь с БД) — для мониторинга и healthcheck.
- Логи — stdout контейнеров (`make logs S=api`), ротация 10 МБ × 3. Персональные данные и токены в логи
  не пишутся.
- Аудит действий — `/admin` → «Журнал аудита» (фильтр по действию).
- Очередь писем — таблица `outbox_messages` (`status`: pending/sent/failed/dropped).
