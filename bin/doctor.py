#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local install checks for the harness. No model or network calls."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_PYTHON = (3, 10)


def check_python() -> list[str]:
    if sys.version_info < MIN_PYTHON:
        return [f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required"]
    return []


def check_command(name: str) -> list[str]:
    return [] if shutil.which(name) else [f"{name} not found on PATH"]


def check_state(root: Path) -> list[str]:
    state = Path(
        os.environ.get("HARNESS_STATE", Path.home() / ".local/state/libreharness")
    ).expanduser()
    if root == state or root in state.parents:
        return [f"HARNESS_STATE must be outside the checkout: {state}"]
    try:
        state.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=state, prefix=".doctor-", delete=True):
            pass
    except OSError as error:
        return [f"HARNESS_STATE is not writable: {error}"]
    return []


def check_config(root: Path) -> list[str]:
    path = root / "opencode.example.json"
    if not path.is_file():
        return ["opencode.example.json is missing"]
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        return [f"opencode.example.json is invalid: {error}"]
    if isinstance(data, dict) and data.get("plugins") == []:
        return []
    return ["opencode.example.json should not load private plugins"]


def check_plugins(root: Path) -> list[str]:
    problems = []
    plugins = root / "plugins"
    if not plugins.is_dir():
        return ["plugins/ is missing"]
    for path in sorted(plugins.glob("*.js")):
        result = subprocess.run(
            ["node", "--check", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            problems.append(f"{path.name}: {result.stderr.strip()[:120]}")
    return problems


def check_tasks(root: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, str(root / "bin/tasks.py"), "--help"],
        capture_output=True,
        text=True,
    )
    return [] if result.returncode == 0 else ["bin/tasks.py --help failed"]


def check_jev(root: Path) -> list[str]:
    if shutil.which("python3") is None:
        return ["python3 not found for Jev"]
    if not (root / "bin/jev_review.py").is_file():
        return []
    key = os.environ.get("JEV_API_KEY") or os.environ.get("JEV_KEY_FILE")
    model = os.environ.get("JEV_MODEL")
    if key and not model:
        return ["JEV_MODEL must be set when a Jev key is configured"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    problems = []
    problems += check_python()
    problems += check_command("node")
    problems += check_command("git")
    problems += check_state(root)
    problems += check_config(root)
    problems += check_plugins(root)
    problems += check_tasks(root)
    problems += check_jev(root)
    if problems:
        print("doctor: FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("doctor: OK")
    print(f"  checkout: {root}")
    print(
        "  state: "
        f"{Path(os.environ.get('HARNESS_STATE', Path.home() / '.local/state/libreharness')).expanduser()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
