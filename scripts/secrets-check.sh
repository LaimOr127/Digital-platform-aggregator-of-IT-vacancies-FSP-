#!/bin/sh
# gitleaks по всей истории git (make secrets-check). История сканируется в клоне во временной папке:
# на томе из iCloud `git log -p` внутри контейнера падает (bus error), и gitleaks сообщал
# «0 commits scanned, no leaks found» — проверка молча ничего не проверяла.
set -eu
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM
git clone -q --mirror --no-local . "$TMP/repo.git"
cp .gitleaks.toml "$TMP/gitleaks.toml"
docker run --rm -v "$TMP:/scan:ro" zricethezav/gitleaks:latest \
  git /scan/repo.git --config /scan/gitleaks.toml --no-banner --redact 2>&1 | tee "$TMP/report.txt"
grep -q "no leaks found" "$TMP/report.txt" || exit 1
if grep -q " 0 commits scanned" "$TMP/report.txt"; then
  echo "gitleaks не просканировал ни одного коммита — проверка недействительна"
  exit 1
fi
