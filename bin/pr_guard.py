# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Check or land one reviewed pull request."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import check_wait

TITLE = re.compile(
    r"^(feat|fix|docs|refactor|perf|test|build|ci|chore|revert)"
    r"(\([^)]+\))?: \S.+$"
)
HEADINGS = ("Why", "What changed", "Scope", "Blast Radius", "Verification")
class GuardError(RuntimeError):
    pass


def run(argv: list[str], repo: Path | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(
        argv,
        cwd=repo,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GuardError(detail or f"{' '.join(argv)} failed")
    return result


def require_github(repo: Path | None = None) -> None:
    if shutil.which("gh") is None:
        raise GuardError(
            "GitHub CLI (gh) is required for this operation; install gh and authenticate, "
            "or mark shipping inapplicable in the task scope"
        )
    result = subprocess.run(
        ["gh", "auth", "status"],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GuardError(
            "GitHub CLI is not authenticated; run gh auth login or mark shipping "
            f"inapplicable in the task scope{': ' + detail if detail else ''}"
        )


def body_problems(body: str) -> list[str]:
    lines = body.splitlines()
    problems = []
    positions = {}
    for index, line in enumerate(lines):
        if line.startswith("## "):
            name = line[3:].strip()
            if name in HEADINGS and name not in positions:
                positions[name] = index
    for name in HEADINGS:
        if name not in positions:
            problems.append(f"body is missing ## {name}")
    ordered = [positions[name] for name in HEADINGS if name in positions]
    if ordered != sorted(ordered):
        problems.append("body headings are out of order")
    return problems


def pr_checks(
    view: dict,
    *,
    expected_head: str,
    base: str,
    require_mergeable: bool = True,
) -> tuple[list[str], str]:
    problems = []
    if view.get("isDraft"):
        problems.append("PR is a draft; open it ready for review")
    if view.get("baseRefName") != base:
        problems.append(f"base is {view.get('baseRefName')}; expected {base}")
    if view.get("headRefOid") != expected_head:
        problems.append("PR head moved; record and review the new head")
    if not TITLE.match(view.get("title") or ""):
        problems.append("title must be type(scope): subject")
    problems.extend(body_problems(view.get("body") or ""))
    if require_mergeable:
        mergeable = view.get("mergeable")
        if mergeable != "MERGEABLE":
            problems.append(f"PR is {mergeable or 'not mergeable'}")
    next_action = "fix"
    return problems, next_action


def local_diff(repo: Path, base: str) -> tuple[dict, list[str]]:
    head = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    dirty = run(["git", "status", "--porcelain"], repo).stdout.strip()
    problems = []
    if dirty:
        problems.append("working tree is not clean; commit the reviewed change")
    output = run(["git", "diff", "--numstat", f"{base}...HEAD"], repo).stdout
    files = []
    changed = 0
    for line in output.splitlines():
        fields = line.split("\t", 2)
        if len(fields) != 3:
            continue
        added, deleted, path = fields
        if added.isdigit():
            changed += int(added)
        if deleted.isdigit():
            changed += int(deleted)
        files.append(path)
    return {
        "head": head,
        "files": len(files),
        "changed_lines": changed,
    }, problems


def gh_json(args: list[str], repo: Path | None = None) -> dict:
    result = run(["gh", *args], repo)
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GuardError(f"gh returned malformed JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise GuardError("gh returned a non-object")
    return value


def pr_view(pr: str, repo: Path | None = None) -> dict:
    return gh_json(
        [
            "pr",
            "view",
            pr,
            "--json",
            "state,isDraft,baseRefName,headRefOid,title,body,additions,"
            "deletions,files,mergeable,mergedAt,url",
        ],
        repo,
    )


def wait_checks(pr: str, repo: Path | None = None, head: str = "") -> None:
    if not head:
        raise GuardError("wait_checks needs the reviewed head")
    try:
        check_wait.wait_for_checks(
            pr=pr,
            head=head,
            repo_path=repo,
            timeout=300,
            interval=20,
        )
    except check_wait.CheckWaitError as exc:
        raise GuardError(str(exc)) from exc


def merge_pr(pr: str, head: str, repo: Path | None = None) -> None:
    run(["gh", "pr", "merge", pr, "--merge", "--match-head-commit", head], repo)


def is_merged(view: dict) -> bool:
    return bool(view.get("mergedAt")) or view.get("state") == "MERGED"


def land(
    pr: str,
    expected_head: str,
    *,
    repo: Path,
    base: str,
    view=pr_view,
    checks=wait_checks,
    merge=merge_pr,
    pause=time.sleep,
) -> dict:
    current = view(pr, repo)
    if is_merged(current):
        return {"ok": True, "pr": pr, "head": expected_head, "state": "MERGED"}
    problems, next_action = pr_checks(
        current,
        expected_head=expected_head,
        base=base,
        require_mergeable=False,
    )
    if problems:
        return {
            "ok": False,
            "pr": pr,
            "head": current.get("headRefOid"),
            "next": next_action,
            "problems": problems,
        }
    try:
        checks(pr, repo, expected_head)
    except GuardError as exc:
        current = view(pr, repo)
        if is_merged(current):
            return {"ok": True, "pr": pr, "head": expected_head, "state": "MERGED"}
        return {
            "ok": False,
            "pr": pr,
            "head": expected_head,
            "next": "fix",
            "problems": [f"required checks failed: {exc}"],
        }
    current = view(pr, repo)
    if current.get("headRefOid") != expected_head:
        return {
            "ok": False,
            "pr": pr,
            "head": current.get("headRefOid"),
            "next": "rereview",
            "problems": ["head moved while checks ran; review the new head"],
        }
    mergeable = current.get("mergeable")
    for _attempt in range(6):
        if mergeable != "UNKNOWN":
            break
        pause(5)
        current = view(pr, repo)
        if is_merged(current):
            return {"ok": True, "pr": pr, "head": expected_head, "state": "MERGED"}
        mergeable = current.get("mergeable")
    if mergeable == "UNKNOWN":
        return {
            "ok": False,
            "pr": pr,
            "head": expected_head,
            "next": "wait",
            "problems": ["forge has not resolved mergeability yet"],
        }
    if mergeable != "MERGEABLE":
        return {
            "ok": False,
            "pr": pr,
            "head": expected_head,
            "next": "fix",
            "problems": [f"PR is {mergeable or 'not mergeable'}"],
        }
    try:
        merge(pr, expected_head, repo)
    except GuardError as exc:
        current = view(pr, repo)
        if is_merged(current):
            return {"ok": True, "pr": pr, "head": expected_head, "state": "MERGED"}
        return {
            "ok": False,
            "pr": pr,
            "head": expected_head,
            "next": "fix",
            "problems": [f"merge failed: {exc}"],
        }
    current = view(pr, repo)
    merged = bool(current.get("mergedAt")) or current.get("state") == "MERGED"
    return {
        "ok": merged,
        "pr": pr,
        "head": current.get("headRefOid"),
        "state": current.get("state"),
        "next": None if merged else "wait",
        "problems": [] if merged else ["merge returned without MERGED state"],
    }


def local_check(
    repo: Path,
    *,
    base: str,
    title: str,
    body_file: Path | None,
) -> dict:
    details, problems = local_diff(repo, base)
    if not TITLE.match(title):
        problems.append("title must be type(scope): subject")
    if body_file is not None:
        try:
            body = body_file.read_text()
        except OSError as exc:
            problems.append(str(exc))
        else:
            problems.extend(body_problems(body))
    next_action = "open"
    if problems:
        next_action = "fix"
    return {
        "ok": not problems,
        **details,
        "next": next_action,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--repo", default=".")
    check.add_argument("--base", default="main")
    check.add_argument("--title", required=True)
    check.add_argument("--body-file")
    check_pr = sub.add_parser("check-pr")
    check_pr.add_argument("--repo", default=".")
    check_pr.add_argument("--pr", required=True)
    check_pr.add_argument("--base", default="main")
    check_pr.add_argument("--head", required=True)
    land_parser = sub.add_parser("land")
    land_parser.add_argument("--repo", default=".")
    land_parser.add_argument("--pr", required=True)
    land_parser.add_argument("--head", required=True)
    land_parser.add_argument("--base", default="main")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if args.command == "check":
        data = local_check(
            repo,
            base=args.base,
            title=args.title,
            body_file=Path(args.body_file) if args.body_file else None,
        )
        print(json.dumps(data, indent=2))
        return 0 if data["ok"] else 1
    try:
        require_github(repo)
        if args.command == "check-pr":
            view = pr_view(args.pr, repo)
            problems, next_action = pr_checks(
                view, expected_head=args.head, base=args.base
            )
            data = {
                "ok": not problems,
                "pr": args.pr,
                "head": args.head,
                "next": next_action if problems else "wait",
                "problems": problems,
            }
        else:
            data = land(
                args.pr,
                args.head,
                repo=repo,
                base=args.base,
            )
    except GuardError as exc:
        data = {
            "ok": False,
            "pr": args.pr,
            "next": "fix",
            "problems": [str(exc)],
        }
    print(json.dumps(data, indent=2))
    return 0 if data["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
