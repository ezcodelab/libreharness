#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install or check the canonical Gitea auto-merge gate.

The gate is deliberately identical in every Gitea repository: it reads the
repository's own base-controlled `.github/merge-policy.json` instead of
hard-coding paths in the workflow. This script keeps the copies from drifting.

Usage:
    python3 bin/sync_gitea_gate.py --target ../brain --target ../aequitas
    python3 bin/sync_gitea_gate.py --check --target ../brain
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "gitea-auto-merge.yml"
GITEA_DEST = Path(".gitea/workflows/auto-merge.yml")
GITHUB_DEST = Path(".github/workflows/auto-merge.yml")
POLICY = Path(".github/merge-policy.json")


def destination(target: Path) -> Path:
    """Gitea scans .gitea/workflows first and ignores .github/workflows if it exists."""
    if (target / ".gitea/workflows").is_dir():
        return target / GITEA_DEST
    return target / GITHUB_DEST


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        type=Path,
        help="repository root; repeatable",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when a target differs",
    )
    args = parser.parse_args()

    if not TEMPLATE.is_file():
        print(f"sync_gitea_gate: missing template {TEMPLATE}", file=sys.stderr)
        return 2

    failed = False
    wanted = digest(TEMPLATE)
    for target in args.target:
        target = target.resolve()
        active = destination(target)
        inactive = target / (GITHUB_DEST if active == target / GITEA_DEST else GITEA_DEST)
        policy = target / POLICY
        if not target.is_dir():
            print(f"sync_gitea_gate: not a directory: {target}", file=sys.stderr)
            failed = True
            continue
        if not policy.is_file():
            print(
                f"sync_gitea_gate: missing {policy}; add the policy first",
                file=sys.stderr,
            )
            failed = True
            continue
        if (target / ".gitea/workflows").is_dir():
            try:
                protected = json.loads(policy.read_text()).get(
                    "protected_paths", []
                )
            except (OSError, json.JSONDecodeError, AttributeError):
                print(
                    f"sync_gitea_gate: policy is not valid JSON: {policy}",
                    file=sys.stderr,
                )
                failed = True
                continue
            if not any(
                item == ".gitea/" or item == ".gitea/workflows/"
                for item in protected
            ):
                print(
                    "sync_gitea_gate: policy must protect .gitea/ or "
                    f".gitea/workflows/ because {target} uses that layout",
                    file=sys.stderr,
                )
                failed = True
                continue
        inactive_dir = inactive.parent
        if inactive_dir.is_dir():
            stray = sorted(
                path.name
                for path in inactive_dir.iterdir()
                if path.suffix in (".yml", ".yaml")
            )
            if stray:
                print(
                    "sync_gitea_gate: workflow in the non-scanned directory "
                    f"{inactive_dir}: {', '.join(stray)}; Gitea only reads "
                    f"{active.parent}",
                    file=sys.stderr,
                )
                failed = True
                continue
        if active.is_file() and digest(active) == wanted:
            print(f"gate OK {target}")
            continue
        if args.check:
            print(f"gate DRIFT {target}: {active}", file=sys.stderr)
            failed = True
            continue
        active.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATE, active)
        active.chmod(0o644)
        print(f"gate written {active}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
