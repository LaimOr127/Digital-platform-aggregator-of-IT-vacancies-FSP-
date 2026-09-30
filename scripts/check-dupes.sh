#!/bin/sh
# Ищет копии файлов от синхронизации iCloud/Finder ("config 2.py", "HEAD 2").
# Они ломают сборку (лишняя миграция Alembic) и git. Код выхода 1 — копии найдены.
set -eu
cd "$(dirname "$0")/.."
found="$(find . -path ./.git/objects -prune -o -path '*/node_modules' -prune -o -name '* [0-9]*' -print)"
if [ -n "$found" ]; then
  echo "Найдены копии файлов от синхронизации (проект лежит в папке iCloud?):"
  echo "$found" | sed 's/^/  /'
  echo "Удалите их (оригиналы — файлы без ' 2' в имени) и повторите."
  exit 1
fi
