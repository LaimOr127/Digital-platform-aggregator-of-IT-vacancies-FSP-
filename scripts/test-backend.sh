#!/bin/sh
# Линт и тесты бэка в контейнерах (на ПК ничего не ставится): make test-backend
# 1) быстрый прогон на SQLite; 2) полный прогон на одноразовом PostgreSQL с миграциями и RLS.
set -eu
IMAGE=itmatch/api:test
NET=itmatch-test-$$
PG=itmatch-test-pg-$$
PASS="$(openssl rand -hex 16)"

cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

docker build -q --target test -t "$IMAGE" backend >/dev/null
echo "== тесты на SQLite"
docker run --rm "$IMAGE"

echo "== тесты на PostgreSQL (миграции + RLS)"
docker network create --internal "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD="$PASS" -e POSTGRES_DB=itmatch_test \
  postgres:16-alpine >/dev/null
i=0; until docker exec "$PG" pg_isready -U postgres -d itmatch_test >/dev/null 2>&1; do
  i=$((i+1)); [ $i -ge 60 ] && { echo "PostgreSQL не поднялся"; exit 1; }; sleep 1
done
docker run --rm --network "$NET" \
  -e TEST_POSTGRES_URL="postgresql+asyncpg://postgres:$PASS@$PG:5432/itmatch_test" \
  "$IMAGE" pytest -q -p no:cacheprovider --cov
