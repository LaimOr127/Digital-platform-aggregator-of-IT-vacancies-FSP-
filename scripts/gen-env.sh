#!/bin/sh
# Создаёт .env из .env.example, заполняя пустые секреты случайными значениями.
# Существующий .env не перезаписывается. Права файла: 600 (только владелец).
set -eu
cd "$(dirname "$0")/.."
if [ -f .env ]; then echo ".env уже существует — не трогаю"; exit 0; fi
umask 077
rand() { openssl rand -hex "$1"; }
while IFS= read -r line; do
  case "$line" in
    DB_OWNER_PASSWORD=|APP_DB_PASSWORD=) echo "${line}$(rand 24)" ;;
    JWT_SECRET=) echo "${line}$(rand 32)" ;;
    FIELD_ENCRYPTION_KEY=) echo "${line}$(rand 32)" ;;
    *) echo "$line" ;;
  esac
done < .env.example > .env
chmod 600 .env
echo ".env создан (секреты сгенерированы локально, в git не попадут)"
