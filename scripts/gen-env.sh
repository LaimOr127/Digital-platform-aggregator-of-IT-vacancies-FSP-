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

# GitHub Codespaces: сайт открыт на проброшенном порту, а не на localhost — туда же ведут ссылки
# в письмах (подтверждение почты, сброс пароля). Заменяем только значение по умолчанию.
codespaces_url() {
  [ -n "${CODESPACE_NAME:-}" ] && grep -q '^PUBLIC_URL=http://localhost' .env || return 0
  port=$(sed -n 's/^HTTP_PORT=//p' .env)
  url="https://${CODESPACE_NAME}-${port:-8088}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  sed "s|^PUBLIC_URL=.*|PUBLIC_URL=$url|" .env > .env.tmp && mv .env.tmp .env
  echo "PUBLIC_URL для Codespaces: $url"
}

if [ ! -f .env ]; then
  while IFS= read -r line; do fill "$line"; done < .env.example > .env
  codespaces_url
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
codespaces_url
chmod 600 .env
if [ -n "$added" ]; then echo ".env дополнен новыми ключами:$added"; else echo ".env актуален"; fi
