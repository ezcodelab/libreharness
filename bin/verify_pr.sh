#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail

BASE_ROOT="${BASE_ROOT:-.}"
PR_ROOT="${PR_ROOT:-.}"

python3 "$BASE_ROOT/bin/docs_lint.py" "$PR_ROOT" --skills-dir "$PR_ROOT/skills"
python3 "$BASE_ROOT/bin/check_spdx.py" --root "$PR_ROOT"
python3 "$BASE_ROOT/bin/scan_private.py" --root "$PR_ROOT"
