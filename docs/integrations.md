# Интеграции

Каждая внешняя система спрятана за интерфейсом в `backend/app/integrations/`. Сценарии
(`services/`) знают только интерфейс, поэтому мок заменяется настоящей системой без правок
бизнес-логики, а в тестах подставляется подделка.

| Система | Интерфейс | Реализации | Где выбирается |
|---|---|---|---|
| ФСП | `FspClient` (Protocol) | `HttpFspClient` (мок `fsp-mock` или реальный API — один контракт), `tests/fake_fsp.FakeFspClient` | `api/deps.get_fsp_client`, worker `__main__` |
| Почта | `Notifier` (ABC) | `SmtpNotifier`, `tests/fake_notifier.MemoryNotifier` | worker `__main__` |
| Языковые модели | `AiClient` (ABC) | `OpenAiCompatibleClient`, `AnthropicClient` | `services/ai_providers.build_client` по записи в БД |
| Подпись паспорта | `PassportSigner` | Ed25519 | `core/signing.py` |

## ФСП

### Контракт (что ждёт бэкенд)

База — `FSP_BASE_URL` + `/api/v1`, заголовок `X-Api-Key: FSP_API_KEY`, таймаут `FSP_TIMEOUT_SECONDS`.

| Запрос | Ответ |
|---|---|
| `GET /athletes/{id}` | `{id, full_name, region, rank}` |
| `GET /athletes/{id}/results` | `[{external_id, discipline, competition_title, level, date, place, stage, role, team}]` |
| `GET /athletes/{id}/questionnaire` | `{email, city, organization, specialization, experience_years, stack[], about, phone, telegram}` |
| `POST /verification/start {athlete_id}` | `{request_id, email_masked, expires_in, demo_code?}` — ФСП отправляет код на почту спортсмена |
| `POST /verification/confirm {request_id, code}` | `{athlete_id}` |

Коды ответа: `404` — нет спортсмена, `400` — неверный код, `429` — лимит попыток, остальное ≥300 и сетевые
ошибки — «ФСП недоступна» (`503` наружу). Ответ вне контракта отклоняется (`_parse`). ID спортсмена
проверяется регулярным выражением до запроса — путь не подставить.

Справочники: дисциплины (`product`, `algorithmic`, `security`, `drones`, `robotics`), уровни
(`regional`, `national`, `international`), этапы (`final` и др.).

### Сценарии

1. **Привязка** (`services/fsp.py`): кандидат вводит ID → `start_verification` → код приходит на почту
   из аккаунта ФСП (10 минут, 5 попыток) → `confirm_verification` → `fsp_links` (один аккаунт ФСП — один
   профиль), загрузка результатов, категории, тир `verified_fsp`. В dev `FSP_DEMO_CODES=true` показывает
   код в интерфейсе (мок возвращает `demo_code`).
2. **Синхронизация** (`services/fsp_sync.py`, задача `FspSyncJob` каждые 5 минут): берёт пачку привязок,
   у которых подошёл срок (`FOR UPDATE SKIP LOCKED` + аренда 10 минут), обновляет достижения по хешу
   исходных данных, пересчитывает категории; изменение данных отзывает паспорт. Сбой — повтор
   с паузой 15 мин → 30 мин → … до суток. Спортсмен удалён в ФСП — привязка снимается.
   Интервал между синхронизациями — `FSP_SYNC_INTERVAL_MINUTES` (6 часов).
3. **Анкета** (`services/profile_import.py`): только для подтверждённой привязки, каждое чтение — в аудите.

### Мок `fsp-mock`

FastAPI с тем же контрактом и демо-спортсменами `FSP-24001…24007`, `FSP-29999` (для смоук-теста).
Данные — в `fsp-mock/app/data.py`. В prod-сборке коды не возвращаются, если не задан
`FSP_DEMO_CODES_PROD=true` (демо-стенд; паспорта тогда помечаются как демо).

### Как подключить реальный API ФСП

1. Убедиться, что API отдаёт поля контракта (или написать адаптер: новый класс с методами `FspClient`
   и выбор его в `get_fsp_client` и в `worker/__main__.py`).
2. В `.env`: `FSP_BASE_URL=https://…`, `FSP_API_KEY=…`. В prod api и worker уже в сети `egress`.
3. Не запускать `fsp-mock`: `make prod S="db migrate api worker web proxy"`.
4. Проверить: `make verify` (смоук использует мок — для реального API проверить привязку вручную).

## Почта

```
сервис (одна транзакция с действием) ──Outbox.enqueue──> outbox_messages (параметры зашифрованы)
worker OutboxJob (каждые 5 с) ──> адрес на момент отправки ──> шаблон (services/emails.py) ──> Notifier.send
```

- Письмо уходит, только если действие закоммичено; ответ API не ждёт SMTP.
- Адресат определяется при отправке: заблокированному или удалённому не уходит (`dropped`).
- Сбой — повтор с паузой, до 8 попыток (`failed`). Параметры стираются после отправки.
- Шаблоны: `verify_email`, `account_exists`, `password_reset`, `offer_received`, `offer_answered`,
  `company_status`, `interview_invited`, `interview_scheduled`, `interview_declined`, `interview_cancelled`,
  `interview_result`. Время в письмах — по Москве. Письма компании — без персональных данных кандидата.
- Новый шаблон: функция-рендерер в `services/emails.py`, запись в `TEMPLATES`, вызов `Outbox.enqueue`
  в сервисе, пример в `tests/test_outbox.py::test_every_template_renders_with_signature`.

### Настройка SMTP на стенде

Локально письма ловит Mailpit (`http://localhost:8025`), наружу ничего не уходит. На сервере Mailpit не
запускается — без SMTP письма копятся в очереди и не доходят (поэтому на тестовом стенде «не пришло письмо»).
В `.env`:

```env
PUBLIC_URL=https://ваш-домен            # ссылки в письмах
SMTP_HOST=smtp.yandex.ru                 # пример: Яндекс 360 / Яндекс Почта
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USER=no-reply@ваш-домен
SMTP_PASSWORD=<пароль приложения>        # в Яндексе: «Пароли приложений», не основной пароль
SMTP_FROM=IT Match <no-reply@ваш-домен>
```

Затем `make prod` (worker перечитает настройки). Подойдёт любой SMTP: Mail.ru, Unisender Go, SendPulse,
Amazon SES. Для доставки в «Входящие», а не в спам, у домена должны быть SPF, DKIM и DMARC.

Пока SMTP не настроен, адрес тестового пользователя подтверждает оператор: `make confirm-email EMAIL=...`
(см. `operations.md`).

### Telegram и другие каналы

Новый канал — реализация `Notifier` (`send(Email)`), выбор в `worker/__main__.py`. Для Telegram нужна
привязка чата к пользователю (новая таблица и бот) — в бэклоге.

## Языковые модели

- Подключаются суперадмином в интерфейсе `/admin/ai`; хранятся в `ai_providers`, ключ — зашифрован,
  наружу — только последние символы. Активна одна модель. Запасной вариант — `ANTHROPIC_API_KEY` в `.env`.
- Типы:
  - `openai` — любой OpenAI-совместимый `POST {base_url}/chat/completions` (OpenAI, DeepSeek, OpenRouter,
    YandexGPT через совместимый шлюз, Ollama, vLLM, LM Studio). Сначала с `response_format: json_object`,
    при отказе сервера — повтор без него; JSON достаётся и из блока ```json.
  - `anthropic` — Messages API с инструментом `respond` (ответ строго по JSON-схеме).
- Использование сейчас: разбор резюме (`services/resume/llm.py`) — только с согласия кандидата и **без
  контактов** (e-mail, телефоны, ссылки вырезаются до отправки). Ответ проверяется схемой Pydantic
  и справочником навыков; при любой ошибке работает алгоритм на правилах.
- **Защита от SSRF** (`integrations/ai/guard.py`): адрес проверяется при сохранении (схема, служебные
  имена стенда, IP-литералы) и перед каждым запросом — по адресам, в которые резолвится имя: loopback,
  link-local (метаданные облака), multicast, зарезервированные и частные сети закрыты. Разрешения:
  `AI_ALLOW_HTTP=true` (http для локальной модели), `AI_ALLOW_PRIVATE_NETWORK=true` (on-prem модель).
- Новый тип API: класс-наследник `AiClient` с `_request`, значение в `AiProviderKind`, ветка
  в `build_client`, шаблон в `frontend/src/features/admin/ai/presets.ts`.
- Новая функция на ИИ: свой парсер по образцу `AiResumeParser` — системный промпт, JSON-схема ответа,
  модель Pydantic для проверки и запасной путь без ИИ.

## Паспорт навыков: проверка подписи

Паспорт — JSON (`payload`), подписанный Ed25519 по каноничной сериализации:
`json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` в UTF-8.

Проверить без доверия к нашему серверу:

1. `GET /api/v1/public/passport-key` → `{algorithm: "Ed25519", key_id, public_key}` (base64, 32 байта) —
   ключ можно сохранить заранее.
2. `GET /api/v1/public/passport/{id}` → `{status, valid, payload, signature, key_id, ...}`.
3. Проверить `signature` (base64) над каноничным `payload` публичным ключом; `key_id` = первые 16 hex
   SHA-256 от ключа.

Отозванный паспорт отдаёт только факт отзыва, без данных. Ключ подписи — `PASSPORT_SIGNING_KEY`
(32 байта hex); при смене ключа старые паспорта перестают проверяться — их нужно перевыпустить.
