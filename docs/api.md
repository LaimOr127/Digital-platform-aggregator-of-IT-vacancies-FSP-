# API: как с ним взаимодействовать

REST поверх HTTPS, JSON, префикс `/api/v1`. Живая схема — `/api/openapi.json`, документация —
`/api-docs/` (Swagger UI без внешних CDN, собирается вместе с фронтом). Типы фронта генерируются из этой схемы, поэтому
описание каждого поля и ограничения — в OpenAPI; здесь — правила, которые схема не показывает.

## Способы взаимодействия

| Канал | Кто | Как защищён |
|---|---|---|
| REST API `/api/v1/*` | SPA и любые клиенты | access-токен `Authorization: Bearer`, роли через AccessPolicy, RLS в БД |
| Ссылки из писем (`/verify-email#token=…`, `/reset-password#token=…`) | владелец ящика | одноразовый токен во фрагменте URL (не уходит в логи прокси), в БД — хеш |
| Публичная проверка паспорта `/passport/<id>` и `GET /public/passport/{id}` | любой работодатель | подпись Ed25519, ключ — `GET /public/passport-key` |
| CLI на сервере (`make create-admin`, `reset-admin-2fa`, `confirm-email`, `seed-demo`) | оператор сервера | доступ к shell сервера |
| Worker → внешние системы | сервер | ФСП (API-ключ), SMTP, модели ИИ (ключ в БД зашифрован) |

Входящих вебхуков нет: данные ФСП забираются запросами (привязка и периодическая синхронизация).

## Аутентификация

1. `POST /auth/register/candidate|employer` → `202` «проверьте почту» — **всегда**, даже если адрес занят
   (владельцу занятого адреса уходит письмо «аккаунт уже есть»). Сессии нет.
2. Ссылка из письма → `POST /auth/verify-email {token}` → `204`.
3. `POST /auth/login {email, password}`:
   - кандидат и работодатель → `{access_token, token_type, expires_in}` + cookie `refresh_token`
     (httpOnly, `SameSite=Strict`, `Path=/api/v1/auth`, `Secure` по HTTPS) и `csrf_token` (читается JS);
   - администратор → `{mfa_required: true, mfa_token, enrolled}` (5 минут, одноразовый). Первый вход —
     `POST /auth/2fa/setup {mfa_token, enrollment_code}` (код подключения выдаёт CLI) → секрет и
     `otpauth://` для QR; затем `POST /auth/2fa/verify {mfa_token, code}` → токены.
   - почта не подтверждена → `403 email_not_verified`.
4. Access-токен живёт 15 минут, хранится только в памяти клиента. Обновление —
   `POST /auth/refresh` с заголовком `X-CSRF-Token: <значение cookie csrf_token>`. Refresh-токен
   одноразовый: повторное использование отзывает всю цепочку (признак кражи). Сессия кандидата
   и работодателя — 14 дней, администратора — 12 часов без продления.
5. `POST /auth/logout` (тоже с CSRF) отзывает refresh-токен.

Клиент обязан: на `401` один раз вызвать refresh и повторить запрос; параллельные refresh не делать
(во фронте — общий промис и Web Locks между вкладками). `403` — не повод обновлять токен.

## Формат ответов

- Успех: JSON по схеме; `204` без тела; `202` — принято (письмо будет отправлено).
- Ошибка — всегда:
  ```json
  {"error": {"code": "conflict", "message": "текст для человека", "details": [...]}}
  ```
  `details` есть только у `validation_error` (422): `[{loc: ["body", "salary_max"], msg: "..."}]` —
  фронт раскладывает их по полям формы. Сообщения на русском.

| Код | HTTP | Когда |
|---|---|---|
| `validation_error` | 422 | тело или параметры не прошли схему |
| `unknown_skills`, `null_not_allowed`, `invalid_slot`, `unsupported_file`, `unsafe_url` | 422 | доменная проверка полей |
| `unauthorized` | 401 | нет токена, истёк, неверный логин/пароль |
| `mfa_expired` | 401 | шаг 2FA надо начать заново |
| `forbidden` | 403 | роль или владелец не те |
| `wrong_password` | 403 | неверный пароль при подтверждении действия (сессия при этом жива) |
| `email_not_verified` | 403 | вход до подтверждения почты |
| `not_found` | 404 | нет строки или она чужая (чужие строки неотличимы от несуществующих) |
| `invalid_link` | 400 | ссылка из письма устарела или использована |
| `invalid_cursor` | 400 | курсор пагинации испорчен |
| `conflict` | 409 | дубликат (адрес, привязка ФСП, повторное приглашение) |
| `invalid_state` | 409 | действие не подходит к текущему статусу (оффер уже принят, грейд не указан) |
| `rate_limited` | 429 | превышен лимит |
| `fsp_verification_failed` | 400 | неверный или истёкший код ФСП |
| `service_unavailable` | 503 | ФСП или модель ИИ недоступны |

## Пагинация, идемпотентность, лимиты

- **Курсорная пагинация**: `?limit=20&cursor=<next_cursor>` → `{items, next_cursor}`; `next_cursor: null`
  — конец. Курсор непрозрачный (дата создания + id, base64), стабилен при вставках. Максимум `limit` —
  50–100 в зависимости от списка. Каталог с подбором по вакансии использует курсор-смещение (`m<n>`).
- **Идемпотентность**: `POST /employer/offers` принимает `Idempotency-Key` (до 64 символов `[A-Za-z0-9_-]`):
  повтор с тем же ключом возвращает тот же оффер, а не создаёт второй; ключ, уже использованный
  для другого оффера, — `409 conflict`.
- **Лимиты** (скользящее окно, общие для всех процессов — счётчики в PostgreSQL):

| Область | Ключ | По умолчанию |
|---|---|---|
| вход, регистрация, удаление аккаунта | IP (IPv6 — сеть /64) | 10/мин |
| вход и подтверждение пароля в один аккаунт | email или id пользователя | 5/мин |
| refresh | IP | 60/мин |
| письма на один адрес | адрес | 3/час |
| код 2FA | администратор | 10/час |
| привязка ФСП | пользователь / аккаунт ФСП | 10/час / 5/час |
| подтверждение кода ФСП, синхронизация | пользователь | 20/час, 10/мин |
| офферы, приглашения | компания | 50/сутки, 100/сутки |
| разбор резюме | пользователь | 20/час |

## Эндпоинты

Роль в скобках — кто может вызвать. Полные схемы — в `/api-docs/`.

**health, public** (без входа): `GET health`, `GET health/ready`, `GET public/skills`,
`GET public/passport/{id}`, `GET public/passport-key`.

**auth**: `register/candidate`, `register/employer`, `verify-email`, `verify-email/resend`,
`password/forgot`, `password/reset`, `login`, `2fa/setup`, `2fa/verify`, `refresh`, `logout`, `GET me`.

**candidate** (кандидат):

| Метод и путь | Что делает |
|---|---|
| `GET/PATCH profile` | свой профиль: стек, грейд, формат, город, вилка, контакты, статус поиска, скрытие |
| `POST account/delete {password}` | удалить аккаунт и все данные (152-ФЗ) |
| `GET import/capabilities`, `GET import/fsp`, `POST import/resume` | черновик профиля из анкеты ФСП или резюме (multipart, `use_ai`) |
| `GET fsp`, `POST fsp/link`, `POST fsp/confirm`, `POST fsp/sync`, `DELETE fsp` | привязка аккаунта ФСП кодом, достижения, категории |
| `GET/POST/DELETE passport` | паспорт навыков: выпуск (имя показывать или нет), отзыв |
| `GET insights/salary`, `GET insights/growth` | радар зарплат и путь роста |
| `GET interviews`, `POST interviews/{id}/accept {slot}`, `POST interviews/{id}/decline` | приглашения на собеседование |
| `GET offers`, `POST offers/{id}/accept`, `POST offers/{id}/decline` | офферы; принятие передаёт компании имя и контакты |

**employer** (работодатель; каталог, приглашения и офферы — только одобренная компания):

| Метод и путь | Что делает |
|---|---|
| `GET company` | своя компания и статус модерации |
| `GET/POST vacancies`, `GET/PATCH/DELETE vacancies/{id}`, `POST vacancies/{id}/publish`, `POST vacancies/{id}/close` | вакансии; публикация — на 14 дней |
| `GET insights/salary?grade=&skills=` | рынок зарплат для формы вакансии |
| `GET catalog/categories`, `GET catalog/candidates`, `GET catalog/candidates/{anon_id}` | анонимный каталог; `vacancy_id` — сортировка по соответствию с процентом и факторами |
| `GET/POST interviews`, `POST interviews/{id}/cancel`, `POST interviews/{id}/complete` | собеседования |
| `GET/POST offers`, `POST offers/{id}/withdraw`, `GET offers/{id}/contacts` | офферы и контакты принявшего кандидата |

**admin** (администратор; управление моделями ИИ — только суперадмин): `GET companies`,
`POST companies/{id}/status`, `GET vacancies`, `POST vacancies/{id}/moderation`, `GET users`,
`POST users/{id}/moderation`, `GET audit`, `GET/POST ai-providers`, `PATCH/DELETE ai-providers/{id}`,
`POST ai-providers/{id}/activate`, `POST ai-providers/deactivate`, `POST ai-providers/{id}/test`.
Каждое действие модератора требует причину и пишется в аудит.

## Жизненные циклы

**Компания**: `pending` (после регистрации) → `approved` или `blocked` модератором. Блокировка закрывает
каталог, блокирует вакансии и отзывает неотвеченные офферы.

**Вакансия**: `draft` → `publish` → `active` на 14 дней (`expires_at`) → компания продлевает (`publish`
ещё раз) или закрывает (`closed`). Истёкшая скрыта из выдачи на уровне RLS. Модератор может перевести
в `blocked`; после разблокировки — снова `draft`.

**Собеседование**: компания приглашает с 1–3 слотами (не раньше чем через час и не позже 30 дней),
форматом (онлайн — только https-ссылка, или офис) → `invited` (7 дней на ответ, иначе `expired`) →
кандидат выбирает слот (`scheduled`) или отказывается (`declined`, повтор приглашения — через 30 дней) →
после времени встречи компания отмечает итог `completed` (`passed`/`failed`, отзыв видит кандидат);
до встречи может отменить (`cancelled`).

**Оффер**: только по собеседованию с итогом `passed`, один на собеседование, вилка обязательна →
`sent` (7 дней) → кандидат `accepted` (компании открываются имя и контакты, каждый просмотр — в
`contact_reveals`) или `declined` (повтор от компании — через 30 дней); компания может `withdrawn`;
без ответа — `expired`.

**Кандидат в каталоге**: виден, если профиль не скрыт и статус поиска не `closed`; анонимен (`anon_id`
не связан с id пользователя) до принятия оффера.

## Пример: от регистрации до оффера (curl)

```bash
B=http://localhost:8088/api/v1; J='Content-Type: application/json'
curl -s -H "$J" -d '{"email":"anna@example.org","password":"<пароль>","full_name":"Анна"}' $B/auth/register/candidate
# ссылка из письма (Mailpit http://localhost:8025) → токен из #token=...
curl -s -H "$J" -d '{"token":"<токен>"}' $B/auth/verify-email
TOKEN=$(curl -s -c jar -H "$J" -d '{"email":"anna@example.org","password":"<пароль>"}' $B/auth/login | jq -r .access_token)
curl -s -X PATCH -H "$J" -H "Authorization: Bearer $TOKEN" -d '{"grade":"middle","skills":["python"]}' $B/candidate/profile
curl -s -H "Authorization: Bearer $TOKEN" $B/candidate/insights/salary
```
