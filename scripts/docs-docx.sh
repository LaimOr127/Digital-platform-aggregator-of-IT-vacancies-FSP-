#!/bin/sh
# Единый DOCX сопроводительной документации (make docs-docx): схемы Mermaid рендерятся в PNG
# контейнером mermaid-cli, затем pandoc собирает файлы в один документ. На ПК ничего не ставится.
set -eu
DOCS="architecture.md assessment.md matching.md validation.md integrations.md api.md stack.md operations.md concepts.md"
OUT=docs/build
USER_ID="$(id -u):$(id -g)"
rm -rf "$OUT" && mkdir -p "$OUT"
for doc in $DOCS; do
  if grep -q '```mermaid' "docs/$doc"; then
    docker run --rm -u "$USER_ID" -v "$PWD/docs:/data" minlag/mermaid-cli:11.4.2 \
      -i "/data/$doc" -o "/data/build/$doc" -e png -s 2 -q >/dev/null
  else
    cp "docs/$doc" "$OUT/$doc"
  fi
done
docker run --rm -u "$USER_ID" -v "$PWD/docs/build:/data" pandoc/core:3.6 $DOCS \
  --toc --toc-depth=2 -M lang=ru -M toc-title="Содержание" \
  -M title="IT Match — сопроводительная документация" -o itmatch-docs.docx
echo "$OUT/itmatch-docs.docx"
