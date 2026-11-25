#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wait for required checks to reach a usable terminal state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

FAILED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "stale",
    "startup_failure",
}


class CheckWaitError(RuntimeError):
    pass


def gh_json(
    args: list[str],
    *,
    repo_path: Path | None = None,
    allow: set[int] | None = None,
) -> object:
    try:
        result = subprocess.run(
            ["gh", *args],
            cwd=repo_path,
            text=True,
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise CheckWaitError(f"gh {' '.join(args)} timed out") from exc
    allowed = allow if allow is not None else {0}
    if result.returncode not in allowed:
        detail = (result.stderr or result.stdout).strip()
        raise CheckWaitError(detail or f"gh {' '.join(args)} failed")
    if not result.stdout.strip():
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CheckWaitError(f"gh returned malformed JSON: {exc}") from exc


def repo_slug(repo_path: Path | None = None) -> str:
    value = gh_json(
        ["repo", "view", "--json", "nameWithOwner"],
        repo_path=repo_path,
    )
    if not isinstance(value, dict):
        raise CheckWaitError("cannot resolve the GitHub repository")
    name = value.get("nameWithOwner")
    if not isinstance(name, str) or "/" not in name:
        raise CheckWaitError("cannot resolve the GitHub repository")
    return name.strip()


def required_checks(repo: str, pr: str, *, repo_path: Path | None = None) -> list[str]:
    value = gh_json(
        ["pr", "checks", pr, "--repo", repo, "--required", "--json", "name"],
        repo_path=repo_path,
        allow={0, 1, 8},
    )
    if not isinstance(value, list):
        raise CheckWaitError("required checks response is not a list")
    return sorted(
        {
            item.get("name")
            for item in value
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
    )


def check_runs(repo: str, head: str, *, repo_path: Path | None = None) -> dict[str, dict]:
    value = gh_json(
        ["api", f"repos/{repo}/commits/{head}/check-runs?per_page=100"],
        repo_path=repo_path,
    )
    if not isinstance(value, dict) or not isinstance(value.get("check_runs"), list):
        raise CheckWaitError("check-runs response is malformed")
    runs: dict[str, dict] = {}
    for run in value["check_runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("name"), str):
            continue
        previous = runs.get(run["name"])
        if previous is None or (run.get("started_at") or "") >= (
            previous.get("started_at") or ""
        ):
            runs[run["name"]] = run
    return runs


def evaluate(required: list[str], runs: dict[str, dict]) -> dict[str, list[str]]:
    failed: list[str] = []
    pending: list[str] = []
    stale: list[str] = []
    missing: list[str] = []
    for name in required:
        run = runs.get(name)
        if run is None:
            missing.append(name)
            continue
        status = str(run.get("status") or "unknown")
        conclusion = str(run.get("conclusion") or "")
        completed = bool(run.get("completed_at"))
        if conclusion == "success" and completed:
            if status != "completed":
                stale.append(f"{name}={status}/success")
        elif conclusion in FAILED_CONCLUSIONS or (
            status == "completed" and conclusion
        ):
            failed.append(f"{name}={status}/{conclusion or 'no-conclusion'}")
        else:
            pending.append(f"{name}={status}/{conclusion or 'pending'}")
    return {
        "failed": failed,
        "pending": pending,
        "stale": stale,
        "missing": missing,
    }


def wait_for_checks(
    *,
    repo: str = "",
    pr: str,
    head: str,
    repo_path: Path | None = None,
    timeout: int = 300,
    interval: int = 20,
    no_check_grace: int = 60,
    required_fn=None,
    runs_fn=None,
    clock=time.monotonic,
    sleep=time.sleep,
    log=print,
) -> list[str]:
    repo = repo or repo_slug(repo_path)
    required_fn = required_fn or (
        lambda: required_checks(repo, pr, repo_path=repo_path)
    )
    runs_fn = runs_fn or (
        lambda: check_runs(repo, head, repo_path=repo_path)
    )
    started = clock()
    while True:
        required = required_fn()
        now = clock()
        if not required:
            if now - started >= no_check_grace:
                raise CheckWaitError(
                    "no required checks were reported within "
                    f"{no_check_grace}s for {head}"
                )
            log(f"checks: waiting for required checks to register ({head})")
            sleep(interval)
            continue

        state = evaluate(required, runs_fn())
        if state["failed"]:
            raise CheckWaitError(
                "required checks failed: " + ", ".join(state["failed"])
            )
        if not state["pending"] and not state["missing"]:
            if state["stale"]:
                log(
                    "checks: terminal success accepted despite stale status: "
                    + ", ".join(state["stale"])
                )
            return state["stale"]

        if now - started >= timeout:
            waiting = state["pending"] + state["missing"]
            raise CheckWaitError(
                f"required checks still pending after {timeout}s: "
                + ", ".join(waiting)
            )
        log(
            "checks: waiting for "
            + ", ".join(state["pending"] + state["missing"])
        )
        sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GH_REPO", ""))
    parser.add_argument("--repo-path", default="")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--interval", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        stale = wait_for_checks(
            repo=args.repo,
            pr=args.pr,
            head=args.head,
            repo_path=Path(args.repo_path) if args.repo_path else None,
            timeout=args.timeout,
            interval=args.interval,
        )
    except CheckWaitError as exc:
        print(f"checks: FAIL: {exc}", file=sys.stderr)
        return 1
    suffix = f" (stale status: {', '.join(stale)})" if stale else ""
    print(f"checks: PASS at {args.head}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
