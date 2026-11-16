#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Gate a pull request on evidence, independent verification, and green CI.

This script never pushes. It reads a PR with `gh`, refuses to merge unless the
contract gates hold, and only then runs `gh pr merge --squash`.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

PASS_TOKENS = {"PASS", "PASS+NOTES"}
FAIL_STATES = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "EXPECTED"}
GOOD_STATES = {"SUCCESS", "NEUTRAL"}


def gh(args, timeout=60):
    return subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def gh_json(args):
    result = gh(args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gh failed")
    return json.loads(result.stdout)


def verifier(path):
    text = Path(path).read_text(encoding="utf-8")
    tokens = text.replace(":", " ").split()
    passed = any(token in PASS_TOKENS for token in tokens)
    sha = next(
        (
            token.lower()
            for token in tokens
            if len(token) == 40 and all(char in "0123456789abcdef" for char in token.lower())
        ),
        None,
    )
    return passed, sha


def check_state(check):
    status = str(check.get("status") or check.get("state") or "").upper()
    conclusion = str(check.get("conclusion") or check.get("state") or "").upper()
    if status in FAIL_STATES or conclusion in FAIL_STATES:
        return False, conclusion or status or "pending"
    if conclusion in GOOD_STATES:
        return True, conclusion
    return False, conclusion or status or "unknown"


def evaluate(pr, verifier_path, evidence_path, required, allow_skipped):
    errors = []
    if str(pr.get("state", "")).upper() != "OPEN":
        errors.append("PR is not open")
    if pr.get("isDraft"):
        errors.append("PR is still a draft")
    if str(pr.get("mergeable", "")).upper() != "MERGEABLE":
        errors.append(f"PR is not mergeable: {pr.get('mergeable') or 'unknown'}")
    head = str(pr.get("headRefOid") or "")
    if not head:
        errors.append("PR has no headRefOid")

    passed, sha = verifier(verifier_path)
    if not passed:
        errors.append("independent verifier did not return PASS or PASS+NOTES")
    if not sha:
        errors.append("verifier file has no 40-character head SHA")
    elif head and sha != head.lower():
        errors.append(f"verifier SHA {sha} does not match PR head {head}")

    evidence = Path(evidence_path)
    if not evidence.is_file() or not evidence.read_text(encoding="utf-8").strip():
        errors.append("evidence file is missing or empty")

    checks = pr.get("statusCheckRollup") or []
    if not checks:
        errors.append("PR has no CI checks")
    names = {}
    for check in checks:
        name = str(check.get("name") or check.get("context") or "check")
        ok, state = check_state(check)
        names[name] = state
        if not ok:
            if allow_skipped and state == "SKIPPED":
                continue
            errors.append(f"check {name}: {state}")
    for name in required:
        if name not in names:
            errors.append(f"required check missing: {name}")
        elif names[name] not in GOOD_STATES:
            errors.append(f"required check {name}: {names[name]}")

    return errors, head, names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", help="OWNER/REPO; gh infers it from the checkout by default")
    parser.add_argument("--verifier-pass", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--required-check", action="append", default=[])
    parser.add_argument("--allow-skipped", action="store_true")
    parser.add_argument("--merge", action="store_true", help="merge after all gates pass")
    parser.add_argument("--wait", type=int, default=0, help="seconds to wait for CI")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not shutil.which("gh"):
        print(
            "pr_watch: gh is not installed. Resolve a forge or open the PR and "
            "merge manually; do not push directly to main.",
            file=sys.stderr,
        )
        return 3

    deadline = time.monotonic() + max(args.wait, 0)
    errors = []
    head = ""
    checks = {}
    while True:
        view = ["pr", "view", str(args.pr), "--json",
                "state,isDraft,mergeable,headRefOid,statusCheckRollup,url"]
        if args.repo:
            view.extend(["--repo", args.repo])
        try:
            pr = gh_json(view)
        except (RuntimeError, json.JSONDecodeError) as error:
            print(f"pr_watch: {error}", file=sys.stderr)
            return 3
        errors, head, checks = evaluate(
            pr, args.verifier_pass, args.evidence, args.required_check, args.allow_skipped
        )
        if not errors or time.monotonic() >= deadline:
            break
        time.sleep(max(args.interval, 1))

    summary = {
        "pr": args.pr,
        "head": head,
        "checks": checks,
        "errors": errors,
        "merged": False,
    }
    if errors:
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            for error in errors:
                print(f"pr_watch: {error}", file=sys.stderr)
        return 2

    if not args.merge:
        summary["action"] = "would merge"
        print(json.dumps(summary, indent=2) if args.json else
              f"pr_watch: PASS at {head}; dry run, not merging")
        return 0

    merge = ["pr", "merge", str(args.pr), "--squash", "--match-head-commit", head]
    if args.repo:
        merge.extend(["--repo", args.repo])
    result = gh(merge, timeout=180)
    if result.returncode != 0:
        print(f"pr_watch: merge failed: {result.stderr.strip()}", file=sys.stderr)
        return 3
    summary["merged"] = True
    print(json.dumps(summary, indent=2) if args.json else
          f"pr_watch: merged PR {args.pr} at {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
