#!/bin/sh
# Смоук-тест работающего стека: ./scripts/smoke.sh [BASE_URL]
# Проверяет API, связь с БД, SPA, заголовки безопасности. Код выхода != 0 при любой ошибке.
set -u
BASE="${1:-http://localhost:8088}"
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

H="$(curl -sI "$BASE/")"
for h in Content-Security-Policy Strict-Transport-Security X-Content-Type-Options X-Frame-Options Referrer-Policy Permissions-Policy; do
  check "Заголовок $h" 1 "$(printf '%s' "$H" | grep -ic "^$h:")"
done
check "Заголовок Server скрыт"               0 "$(printf '%s' "$H" | grep -ic '^server:')"

[ $fail -eq 0 ] && echo "ИТОГ: все проверки пройдены" || echo "ИТОГ: есть ошибки"
exit $fail
