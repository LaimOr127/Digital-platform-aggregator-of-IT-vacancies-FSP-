#!/bin/sh
# Создаёт .env из .env.example, заполняя пустые секреты случайными значениями.
# Если .env уже есть — только дописывает ключи, которых в нём нет (после обновления проекта);
# существующие значения не меняются. Права файла: 600 (только владелец).
set -eu
cd "$(dirname "$0")/.."
umask 077
rand() { openssl rand -hex "$1"; }

# строка шаблона -> строка .env (пустые секреты заполняются)
fill() {
  case "$1" in
    DB_OWNER_PASSWORD=|APP_DB_PASSWORD=|FSP_API_KEY=) echo "$1$(rand 24)" ;;
    JWT_SECRET=|FIELD_ENCRYPTION_KEY=|PASSPORT_SIGNING_KEY=) echo "$1$(rand 32)" ;;
    *) echo "$1" ;;
  esac
}

if [ ! -f .env ]; then
  while IFS= read -r line; do fill "$line"; done < .env.example > .env
  chmod 600 .env
  echo ".env создан (секреты сгенерированы локально, в git не попадут)"
  exit 0
fi

added=""
while IFS= read -r line; do
  key="${line%%=*}"
  case "$line" in ''|\#*) continue ;; esac
  if ! grep -q "^${key}=" .env; then
    fill "$line" >> .env
    added="$added $key"
  fi
done < .env.example
chmod 600 .env
if [ -n "$added" ]; then echo ".env дополнен новыми ключами:$added"; else echo ".env актуален"; fi
