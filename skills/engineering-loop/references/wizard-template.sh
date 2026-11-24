#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail

TOTAL_STAGES=1
STAGE=0

stage() {
  STAGE=$((STAGE + 1))
  printf '\n[%d/%d] %s\n' "$STAGE" "$TOTAL_STAGES" "$1"
}

say() { printf '%s\n' "$1"; }

step() { printf '  - %s\n' "$1"; }

ask() {
  local name="$1" prompt="$2"
  printf '%s: ' "$prompt"
  read -r "${name?}"
  export "${name?}"
}

ask_secret() {
  local name="$1" prompt="$2"
  printf '%s: ' "$prompt"
  read -r -s "${name?}"
  printf '\n'
  export "${name?}"
}

confirm() {
  local answer=""
  printf '%s Type yes to continue: ' "$1"
  read -r answer
  [ "$answer" = "yes" ]
}

open_url() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1 || true
  else
    printf 'Open: %s\n' "$1"
  fi
}

write_env() {
  local key="$1" file="${2:-.env}"
  WIZARD_KEY="$key" WIZARD_FILE="$file" python3 - <<'PY'
import os
import pathlib
import re

key = os.environ["WIZARD_KEY"]
path = pathlib.Path(os.environ["WIZARD_FILE"])
value = os.environ.get(key, "")
if "\n" in value or "\r" in value:
    raise SystemExit(f"{key} must be a single line")
quoted = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
line = f"{key}={quoted}\n"
path.parent.mkdir(parents=True, exist_ok=True)
lines = path.read_text().splitlines(keepends=True) if path.exists() else []
pattern = re.compile(rf"^{re.escape(key)}=")
for index, existing in enumerate(lines):
    if pattern.match(existing):
        lines[index] = line
        break
else:
    lines.append(line)
path.write_text("".join(lines))
path.chmod(0o600)
PY
}

set_secret() {
  local name="$1"
  if ! command -v gh >/dev/null 2>&1; then
    printf 'gh is required for %s\n' "$name" >&2
    return 1
  fi
  printenv "$name" | gh secret set "$name" >/dev/null
}

finish() {
  if [ "$STAGE" -ne "$TOTAL_STAGES" ]; then
    printf 'warning: ran %d of %d stages\n' "$STAGE" "$TOTAL_STAGES" >&2
    return 1
  fi
  printf '\nDone. Delete this script unless the setup should be repeatable.\n'
}

run() {
  stage "Create a provider token"
  open_url "https://example.com/tokens"
  say "Open the page, create a read-scoped token, and copy it."
  ask_secret PROVIDER_TOKEN "Paste the token"
  confirm "Write PROVIDER_TOKEN to .env?"
  write_env PROVIDER_TOKEN .env
  step "PROVIDER_TOKEN written to .env with mode 600"
}

if [ "$TOTAL_STAGES" -lt 1 ]; then
  printf 'Set TOTAL_STAGES before running.\n' >&2
  exit 2
fi

run
finish
