#!/bin/sh
# Смоук-тест работающего стека: ./scripts/smoke.sh [BASE_URL]
# Проверяет API, связь с БД, SPA, почту (Mailpit), заголовки безопасности.
# Код выхода != 0 при любой ошибке.
set -u
BASE="${1:-http://localhost:8088}"
MAIL="${MAIL_URL:-http://localhost:${MAIL_UI_PORT:-8025}}"  # Mailpit: почтовый ящик dev-стенда
fail=0
check() { # имя, ожидаемое, фактическое
  if [ "$2" = "$3" ]; then echo "  OK   $1"; else echo "  FAIL $1 (ожидалось: $2, получено: $3)"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "Смоук-тест: $BASE"
# ждём готовности до 90 секунд (первый старт БД)
i=0; until [ "$(code "$BASE/api/v1/health/ready")" = "200" ] || [ $i -ge 45 ]; do i=$((i+1)); sleep 2; done

check "API жив (/api/v1/health)"            '{"status":"ok"}'    "$(curl -s "$BASE/api/v1/health")"
check "API видит БД (/api/v1/health/ready)"  '{"status":"ready"}' "$(curl -s "$BASE/api/v1/health/ready")"
check "Документация API (/api-docs/)"        200 "$(code "$BASE/api-docs/")"
check "OpenAPI-схема"                        200 "$(code "$BASE/api/openapi.json")"
check "Единый формат ошибки 404"             1   "$(curl -s "$BASE/api/v1/nope" | grep -c '"error"')"
check "Главная страница"                     200 "$(code "$BASE/")"
check "SPA-маршрут портала (/company/x)"     200 "$(code "$BASE/company/x")"
check "Страница содержит приложение"         1   "$(curl -s "$BASE/" | grep -c 'id="root"')"

# Сквозной сценарий через Caddy -> api -> PostgreSQL (миграции, RLS, шифрование)
EMAIL="smoke-$(date +%s)-$$@example.org"
PW="Smoke-pass-$(openssl rand -hex 4)"
J='Content-Type: application/json'
# JSON собираем через printf: фигурные скобки внутри $(...) оболочка может раскрыть
body() { printf '{"email":"%s","password":"%s"%s}' "$EMAIL" "$1" "${2:-}"; }
check "Регистрация кандидата (без раскрытия email)" 202 "$(code -H "$J" -d "$(body "$PW" ',"full_name":"Смоук Тест"')" "$BASE/api/v1/auth/register/candidate")"
check "Вход до подтверждения почты"           403 "$(code -H "$J" -d "$(body "$PW")" "$BASE/api/v1/auth/login")"
# письмо отправляет worker через Mailpit (dev); ссылка подтверждения — из письма
LINK=""; i=0
while [ -z "$LINK" ] && [ $i -lt 20 ]; do
  ID="$(curl -s "$MAIL/api/v1/search?query=to%3A$(printf '%s' "$EMAIL" | sed 's/@/%40/')" | sed -n 's/.*"ID":"\([^"]*\)".*/\1/p' | head -1)"
  [ -n "$ID" ] && LINK="$(curl -s "$MAIL/api/v1/message/$ID" | sed -n 's/.*verify-email#token=\([A-Za-z0-9_-]*\).*/\1/p' | head -1)"
  [ -z "$LINK" ] && { i=$((i+1)); sleep 1; }
done
check "Письмо подтверждения пришло (Mailpit)" 1   "$([ -n "$LINK" ] && echo 1 || echo 0)"
check "Подтверждение почты по ссылке"         204 "$(code -H "$J" -d "{\"token\":\"$LINK\"}" "$BASE/api/v1/auth/verify-email")"
TOKEN="$(curl -s -H "$J" -d "$(body "$PW")" "$BASE/api/v1/auth/login" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')"
check "Вход после подтверждения выдаёт токен" 1   "$([ -n "$TOKEN" ] && echo 1 || echo 0)"
check "Профиль кандидата (RLS + расшифровка)" 1   "$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/candidate/profile" | grep -c 'Смоук Тест')"
check "Вход с неверным паролем"               401 "$(code -H "$J" -d "$(body Wrong-pass-42)" "$BASE/api/v1/auth/login")"
check "Кабинет работодателя закрыт кандидату" 403 "$(code -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/employer/vacancies")"
check "Без токена — 401"                      401 "$(code "$BASE/api/v1/candidate/profile")"

# ФСП и паспорт (только стенд с моком ФСП: код подтверждения возвращается в ответе).
# В конце аккаунт ФСП отвязывается — смоук можно запускать повторно.
AUTH="Authorization: Bearer $TOKEN"
START="$(curl -s -H "$AUTH" -H "$J" -d '{"athlete_id":"FSP-29999"}' "$BASE/api/v1/candidate/fsp/link")"
DEMO="$(printf '%s' "$START" | sed -n 's/.*"demo_code":"\([0-9]*\)".*/\1/p')"
if [ -n "$DEMO" ]; then
  LINKED="$(curl -s -H "$AUTH" -H "$J" -d "{\"code\":\"$DEMO\"}" "$BASE/api/v1/candidate/fsp/confirm")"
  check "Привязка ФСП через мок"                1   "$(printf '%s' "$LINKED" | grep -c '"verification_tier":"verified_fsp"')"
  check "Категория по результатам ФСП"          1   "$(printf '%s' "$LINKED" | grep -c 'robotics-advanced')"
  PID="$(curl -s -H "$AUTH" -H "$J" -d '{"show_name":false}' "$BASE/api/v1/candidate/passport" | sed -n 's/^{"id":"\([^"]*\)".*/\1/p')"
  check "Паспорт навыков проверяется публично"  1   "$(curl -s "$BASE/api/v1/public/passport/$PID" | grep -c '"valid":true')"
  check "Страница паспорта (SPA)"               200 "$(code "$BASE/passport/$PID")"
  check "Паспорт не индексируется"              1   "$(curl -sI "$BASE/passport/$PID" | grep -ic '^x-robots-tag: noindex')"
  check "Отвязка ФСП отзывает паспорт"          204 "$(code -X DELETE -H "$AUTH" "$BASE/api/v1/candidate/fsp")"
  check "Отозванный паспорт не действителен"    1   "$(curl -s "$BASE/api/v1/public/passport/$PID" | grep -c '"valid":false')"
else
  echo "  SKIP ФСП: стенд без демо-кодов (FSP_DEMO_CODES=false)"
fi

H="$(curl -sI "$BASE/")"
for h in Content-Security-Policy Strict-Transport-Security X-Content-Type-Options X-Frame-Options Referrer-Policy Permissions-Policy; do
  check "Заголовок $h" 1 "$(printf '%s' "$H" | grep -ic "^$h:")"
done
check "Заголовок Server скрыт"               0 "$(printf '%s' "$H" | grep -ic '^server:')"

[ $fail -eq 0 ] && echo "ИТОГ: все проверки пройдены" || echo "ИТОГ: есть ошибки"
exit $fail
