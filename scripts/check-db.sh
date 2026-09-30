#!/bin/sh
# Проверка прав роли приложения в работающей БД: make check-db
# Ожидается: роль приложения подключается к своей БД, но не может менять схему и заходить в служебные БД.
set -u
: "${DC:?нужна переменная DC (команда docker compose), запускайте через make check-db}"
val() { grep "^$1=" .env | cut -d= -f2-; }
U="$(val APP_DB_USER)"; P="$(val APP_DB_PASSWORD)"; DB="$(val DB_NAME)"
q() { $DC exec -T -e PGPASSWORD="$P" db psql -h 127.0.0.1 -U "$U" -d "$1" -v ON_ERROR_STOP=1 -tAc "$2" 2>&1; }
fail=0
out="$(q "$DB" "SELECT 1")"
[ "$out" = "1" ] && echo "  OK   роль приложения подключается к $DB" || { echo "  FAIL подключение: $out"; fail=1; }
out="$(q "$DB" "CREATE TABLE _probe(id int)")"
echo "$out" | grep -q "permission denied" && echo "  OK   роль приложения не может менять схему" || { echo "  FAIL DDL разрешён: $out"; fail=1; }
out="$(q postgres "SELECT 1")"
echo "$out" | grep -q "permission denied" && echo "  OK   нет доступа к служебной БД postgres" || { echo "  FAIL доступ к postgres: $out"; fail=1; }
out="$($DC exec -T -e PGPASSWORD=wrong db psql -h 127.0.0.1 -U "$U" -d "$DB" -tAc "SELECT 1" 2>&1)"
echo "$out" | grep -q "password authentication failed" && echo "  OK   неверный пароль отклоняется" || { echo "  FAIL неверный пароль: $out"; fail=1; }
exit $fail
