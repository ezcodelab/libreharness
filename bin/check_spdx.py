#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check SPDX headers on the public tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "state", "__pycache__", ".venv", "bench/results"}
SKIP_FILES = {"LICENSE", "NOTICE", "docs/LICENSE"}
EXPECTED = {
    ".py": "# SPDX-License-Identifier: MIT",
    ".js": "// SPDX-License-Identifier: MIT",
    ".mjs": "// SPDX-License-Identifier: MIT",
    ".sh": "# SPDX-License-Identifier: MIT",
    ".yml": "# SPDX-License-Identifier: MIT",
    ".yaml": "# SPDX-License-Identifier: MIT",
}


def wanted(path: Path, root: Path) -> str | None:
    if path.name in SKIP_FILES:
        return None
    suffix = path.suffix
    if suffix == ".md":
        under_docs = "docs" in path.relative_to(root).parts
        return "<!-- SPDX-License-Identifier: CC-BY-4.0 -->" if under_docs else "<!-- SPDX-License-Identifier: MIT -->"
    return EXPECTED.get(suffix)


def files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in {"package-lock.json", "bun.lock"}:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    problems = []
    for path in files(root):
        expected = wanted(path, root)
        if expected is None:
            continue
        try:
            head = path.read_text(errors="replace")
        except OSError as error:
            problems.append(f"{path.relative_to(root)}: {error}")
            continue
        if expected not in head:
            problems.append(f"{path.relative_to(root)}: missing {expected}")
    if problems:
        print("SPDX check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("SPDX check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
