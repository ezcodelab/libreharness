#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Gate a pull request on evidence, independent verification, and green CI.

GitHub uses `gh`; Gitea uses its REST API and GITEA_TOKEN. The script never
pushes. It schedules or performs a merge only after the contract gates hold.
"""

import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FAIL_STATES = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "EXPECTED"}
GOOD_STATES = {"SUCCESS"}
VERDICT = re.compile(r"^(PASS(?:\+NOTES)?)\s+([0-9a-fA-F]{40})$")
GITEA_PENDING = {"pending", "running"}
GITEA_GOOD = {"success"}


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
    lines = [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        return False, None
    match = VERDICT.fullmatch(lines[0])
    if not match:
        return False, None
    if any(line.upper().startswith("FAIL") for line in lines):
        return False, None
    return True, match.group(2).lower()


def check_state(check):
    status = str(check.get("status") or check.get("state") or "").upper()
    conclusion = str(check.get("conclusion") or check.get("state") or "").upper()
    if status in FAIL_STATES or conclusion in FAIL_STATES:
        return False, conclusion or status or "pending"
    if conclusion in GOOD_STATES:
        return True, conclusion
    return False, conclusion or status or "unknown"


def evaluate_github(pr, verifier_path, evidence_path, required):
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
            errors.append(f"check {name}: {state}")
    for name in required:
        if name not in names:
            errors.append(f"required check missing: {name}")
        elif names[name] not in GOOD_STATES:
            errors.append(f"required check {name}: {names[name]}")

    return errors, head, names


def gitea_api(method, path, payload, api, token, insecure, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{api.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    context = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(request, context=context, timeout=timeout) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:400]
        raise RuntimeError(f"{method} {path}: HTTP {error.code}: {detail}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"{method} {path}: {error.reason}") from None


def evaluate_gitea(pr, status, verifier_path, evidence_path, required, base, allow_pending):
    errors = []
    if str(pr.get("state", "")).lower() != "open":
        errors.append("PR is not open")
    if pr.get("merged"):
        errors.append("PR is already merged")
    if pr.get("mergeable") is not True:
        errors.append(f"PR is not mergeable: {pr.get('mergeable')}")
    base_ref = str((pr.get("base") or {}).get("ref") or "")
    if base_ref != base:
        errors.append(f"PR base is {base_ref or 'unknown'}, expected {base}")
    head = str((pr.get("head") or {}).get("sha") or "")
    if not head:
        errors.append("PR has no head SHA")

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

    statuses = status.get("statuses") or []
    if not statuses:
        errors.append("PR has no status checks")
    names = {}
    for item in statuses:
        name = str(item.get("context") or "check")
        names[name] = str(item.get("status") or "unknown").lower()

    if required:
        for name in required:
            if name not in names:
                errors.append(f"required check missing: {name}")
            elif names[name] not in GITEA_GOOD:
                if allow_pending and names[name] in GITEA_PENDING:
                    continue
                errors.append(f"required check {name}: {names[name]}")
    else:
        for name, state in names.items():
            if state in GITEA_GOOD:
                continue
            if allow_pending and state in GITEA_PENDING:
                continue
            errors.append(f"check {name}: {state}")

    return errors, head, names


def github_merge(args, head):
    merge = ["pr", "merge", str(args.pr), "--squash", "--match-head-commit", head]
    if args.repo:
        merge.extend(["--repo", args.repo])
    result = gh(merge, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gh merge failed")


def run_github(args):
    if args.auto:
        print("pr_watch: --auto is the Gitea path; GitHub uses --merge", file=sys.stderr)
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
        errors, head, checks = evaluate_github(
            pr, args.verifier_pass, args.evidence, args.required_check
        )
        if not errors or time.monotonic() >= deadline:
            break
        time.sleep(max(args.interval, 1))

    summary = {"pr": args.pr, "head": head, "checks": checks, "errors": errors, "merged": False}
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

    try:
        github_merge(args, head)
    except RuntimeError as error:
        print(f"pr_watch: merge failed: {error}", file=sys.stderr)
        return 3
    summary["merged"] = True
    print(json.dumps(summary, indent=2) if args.json else
          f"pr_watch: merged PR {args.pr} at {head}")
    return 0


def run_gitea(args):
    token = os.environ.get("GITEA_TOKEN", "")
    api = args.api or os.environ.get("GITEA_URL", "")
    if not token:
        print("pr_watch: GITEA_TOKEN is not set", file=sys.stderr)
        return 3
    if not api:
        print(
            "pr_watch: GITEA_URL is not set (or pass --api); refusing to guess "
            "the token destination",
            file=sys.stderr,
        )
        return 3
    if not args.repo or "/" not in args.repo:
        print("pr_watch: --repo OWNER/REPO is required for Gitea", file=sys.stderr)
        return 3

    deadline = time.monotonic() + max(args.wait, 0)
    errors = []
    head = ""
    checks = {}
    while True:
        try:
            pr = gitea_api("GET", f"/repos/{args.repo}/pulls/{args.pr}", None, api, token, args.insecure)
            head = str((pr.get("head") or {}).get("sha") or "")
            status = gitea_api(
                "GET", f"/repos/{args.repo}/commits/{head}/status",
                None, api, token, args.insecure,
            ) if head else {}
            errors, head, checks = evaluate_gitea(
                pr, status, args.verifier_pass, args.evidence,
                args.required_check, args.base, allow_pending=args.auto,
            )
        except RuntimeError as error:
            print(f"pr_watch: {error}", file=sys.stderr)
            return 3
        if not errors or args.auto or time.monotonic() >= deadline:
            break
        time.sleep(max(args.interval, 1))

    summary = {
        "pr": args.pr,
        "forge": "gitea",
        "head": head,
        "checks": checks,
        "errors": errors,
        "merged": False,
        "scheduled": False,
    }
    if errors:
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            for error in errors:
                print(f"pr_watch: {error}", file=sys.stderr)
        return 2

    if not args.merge and not args.auto:
        summary["action"] = "would merge"
        print(json.dumps(summary, indent=2) if args.json else
              f"pr_watch: PASS at {head}; dry run, not merging")
        return 0

    payload = {
        "do": "squash",
        "merge_when_checks_succeed": bool(args.auto),
        "head_commit_id": head,
        "delete_branch_after_merge": bool(args.delete_branch),
    }
    try:
        gitea_api(
            "POST", f"/repos/{args.repo}/pulls/{args.pr}/merge",
            payload, api, token, args.insecure, timeout=180,
        )
    except RuntimeError as error:
        print(f"pr_watch: merge failed: {error}", file=sys.stderr)
        return 3

    if args.auto:
        summary["scheduled"] = True
        print(json.dumps(summary, indent=2) if args.json else
              f"pr_watch: scheduled auto-merge for PR {args.pr} at {head}")
    else:
        summary["merged"] = True
        print(json.dumps(summary, indent=2) if args.json else
              f"pr_watch: merged PR {args.pr} at {head}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--repo", help="OWNER/REPO; required for Gitea")
    parser.add_argument("--forge", choices=("auto", "github", "gitea"), default="auto")
    parser.add_argument("--api", help="Gitea API base; defaults to GITEA_URL")
    parser.add_argument("--insecure", action="store_true", help="skip Gitea TLS verification")
    parser.add_argument("--base", default="main", help="required base branch for Gitea")
    parser.add_argument("--verifier-pass", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--required-check", action="append", default=[])
    parser.add_argument("--merge", action="store_true", help="merge immediately after the gate")
    parser.add_argument("--auto", action="store_true", help="schedule Gitea auto-merge after the gate")
    parser.add_argument("--delete-branch", action="store_true", help="delete the Gitea branch after merge")
    parser.add_argument("--wait", type=int, default=0, help="seconds to wait for CI")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.merge and args.auto:
        parser.error("--merge and --auto are mutually exclusive")

    if args.forge == "gitea":
        return run_gitea(args)
    if args.forge == "github":
        return run_github(args)
    if shutil.which("gh"):
        return run_github(args)
    if os.environ.get("GITEA_TOKEN"):
        return run_gitea(args)
    print(
        "pr_watch: no forge found. Install gh, or set GITEA_URL and GITEA_TOKEN; "
        "do not push directly to main.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
