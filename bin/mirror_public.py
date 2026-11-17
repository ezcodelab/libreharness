#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mirror Gitea main and tags to a public GitHub remote.

Gitea is canonical. This script copies only main and tags, never prunes, and
never creates or deletes GitHub branches or releases. It is intended to run on
a host that can reach both remotes, such as the NAS runner.
"""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


class MirrorError(RuntimeError):
    pass


class LockBusy(RuntimeError):
    pass


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_state_dir():
    explicit = os.environ.get("HARNESS_STATE")
    if explicit:
        return Path(explicit).expanduser()
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg) / "libreharness"
    return Path.home() / ".local" / "state" / "libreharness"


def acquire_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = path.open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise LockBusy(f"another mirror run holds {path}") from None
    return handle


def write_status(path, status):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".mirror-status-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(status, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass


def read_status(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def check_status(path, max_age):
    status = read_status(path)
    if not isinstance(status, dict) or not status:
        return False, f"no mirror status at {path}"
    repos = status.get("repos")
    if not isinstance(repos, dict):
        return False, "mirror status has no valid repos field"
    if not status.get("ok"):
        errors = [
            str(item.get("error", "unknown"))
            for item in repos.values()
            if isinstance(item, dict) and item.get("error")
        ]
        return False, "last mirror run failed: " + ("; ".join(errors) or "unknown")
    last = status.get("last_success")
    if not isinstance(last, str) or not last:
        return False, "no successful mirror run recorded"
    try:
        last_at = datetime.fromisoformat(last)
    except (ValueError, TypeError):
        return False, f"invalid last_success timestamp: {last}"
    if last_at.tzinfo is None:
        last_at = last_at.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - last_at).total_seconds()
    if age < 0:
        return False, f"last_success timestamp is {int(-age)}s in the future"
    if age > max_age:
        return False, f"last successful push was {int(age)}s ago (limit {max_age}s)"
    return True, f"last successful push was {int(age)}s ago"


def git(repo, *args, check=True, timeout=300):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git failed"
        raise MirrorError(f"git {' '.join(args)}: {detail}")
    return result


def source_tags(repo, source):
    result = git(repo, "ls-remote", "--tags", "--refs", source)
    tags = []
    for line in result.stdout.splitlines():
        sha, ref = line.split("\t", 1)
        tags.append((ref, sha))
    return tags


def mirror(repo, source, target, dry_run=False):
    repo = Path(repo).resolve()
    if not (repo / ".git").exists():
        raise MirrorError(f"not a git checkout: {repo}")

    git(repo, "fetch", "--no-tags", source, "main")
    git(repo, "fetch", source, "+refs/tags/*:refs/tags/*")
    source_main = f"refs/remotes/{source}/main"
    source_sha = git(repo, "rev-parse", source_main).stdout.strip()

    target_sha = None
    fetched = git(repo, "fetch", "--no-tags", target, "main", check=False)
    if fetched.returncode == 0:
        target_sha = git(repo, "rev-parse", f"refs/remotes/{target}/main").stdout.strip()

    if target_sha and target_sha != source_sha:
        if git(repo, "merge-base", "--is-ancestor", target_sha, source_sha, check=False).returncode != 0:
            raise MirrorError(
                f"{target} main has commits not in {source}/main; refusing to rewrite it"
            )

    tags = source_tags(repo, source)
    if dry_run:
        print(
            f"mirror {repo.name}: main {source_sha} -> {target}; "
            f"{len(tags)} tag(s); dry run"
        )
        return {"repo": repo.name, "main": source_sha, "tags": len(tags)}

    if target_sha != source_sha:
        git(repo, "push", target, f"{source_main}:refs/heads/main")
    for ref, _sha in tags:
        git(repo, "push", target, f"{ref}:{ref}")
    print(
        f"mirror {repo.name}: main {source_sha[:12]}; "
        f"{len(tags)} tag(s) checked"
    )
    return {"repo": repo.name, "main": source_sha, "tags": len(tags)}


def run_once(repos, source, target, status_file, dry_run, previous):
    started = time.monotonic()
    attempt = now_iso()
    results = {}
    failed = False
    for repo in repos:
        repo_name = Path(repo).resolve().name
        old = previous.get("repos", {}).get(repo_name, {})
        try:
            result = mirror(repo, source, target, dry_run=dry_run)
            results[repo_name] = {
                "ok": True,
                "last_success": now_iso(),
                "head": result["main"],
                "tags": result["tags"],
                "error": "",
            }
        except Exception as error:
            failed = True
            results[repo_name] = {
                "ok": False,
                "last_success": old.get("last_success"),
                "head": old.get("head", ""),
                "tags": old.get("tags", 0),
                "error": str(error),
            }
            print(f"mirror {repo_name}: FAIL: {error}", file=sys.stderr)

    finished = now_iso()
    status = {
        "ok": not failed,
        "last_attempt": attempt,
        "last_success": finished if not failed else previous.get("last_success"),
        "duration_seconds": round(time.monotonic() - started, 3),
        "repos": results,
    }
    if not dry_run:
        write_status(status_file, status)
    if failed:
        print("mirror: FAIL", file=sys.stderr)
    else:
        print("mirror: OK")
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Git checkout to mirror; repeatable; defaults to the current directory",
    )
    parser.add_argument("--source", default="origin", help="canonical Gitea remote")
    parser.add_argument("--target", default="github", help="public GitHub remote")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--loop", action="store_true", help="run forever")
    parser.add_argument("--interval", type=int, default=600)
    parser.add_argument(
        "--lock-file",
        default=str(default_state_dir() / "mirror.lock"),
        help="exclusive lock file",
    )
    parser.add_argument(
        "--status-file",
        default=str(default_state_dir() / "mirror-status.json"),
        help="atomic status file",
    )
    parser.add_argument("--check", action="store_true", help="check freshness and exit")
    parser.add_argument("--max-age", type=int, default=1200, help="max seconds since success")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.check:
        ok, detail = check_status(args.status_file, args.max_age)
        if args.json:
            print(json.dumps({"ok": ok, "detail": detail, "status": read_status(args.status_file)}, indent=2))
        else:
            print(f"mirror check: {'OK' if ok else 'FAIL'}: {detail}", file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1

    repos = [Path(item) for item in (args.repo or ["."])]
    try:
        lock = acquire_lock(args.lock_file)
    except LockBusy as error:
        print(f"mirror: skipped: {error}", file=sys.stderr)
        return 0

    try:
        previous = read_status(args.status_file)
        while True:
            status = run_once(
                repos, args.source, args.target, args.status_file, args.dry_run, previous
            )
            if not args.loop:
                return 0 if status["ok"] else 1
            previous = status
            time.sleep(max(args.interval, 10))
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
