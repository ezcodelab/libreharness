#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

NAMES = ("ast-grep", "sg")


def _bin_in(root: Path) -> Path | None:
    for name in NAMES:
        candidate = root / "node_modules" / ".bin" / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _search(start: Path) -> Path | None:
    for parent in (start, *start.parents):
        found = _bin_in(parent)
        if found is not None:
            return found
    return None


def resolve() -> list[str] | None:
    override = os.environ.get("SG_BIN")
    if override:
        return [override]
    executable = shutil.which("ast-grep") or shutil.which("sg")
    if executable:
        return [executable]
    home = Path(os.environ.get("HARNESS_HOME", Path(__file__).resolve().parent.parent))
    found = _search(Path.cwd()) or _search(home)
    if found is not None:
        return [str(found)]
    return None


def main(argv: list[str]) -> int:
    command = resolve()
    if command is None:
        print("ast-grep not found; run npm install or set SG_BIN", file=sys.stderr)
        return 127
    try:
        return subprocess.run([*command, *argv], check=False).returncode
    except OSError as error:
        print(f"ast-grep failed: {error}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
