#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mirror Gitea main and tags to a public GitHub remote.

Gitea is canonical. This script copies only main and tags, never prunes, and
never creates or deletes GitHub branches or releases. It is intended to run on
a host that can reach both remotes, such as the NAS runner.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class MirrorError(RuntimeError):
    pass


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
        return

    if target_sha != source_sha:
        git(repo, "push", target, f"{source_main}:refs/heads/main")
    for ref, _sha in tags:
        git(repo, "push", target, f"{ref}:{ref}")
    print(
        f"mirror {repo.name}: main {source_sha[:12]}; "
        f"{len(tags)} tag(s) checked"
    )


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
    args = parser.parse_args()

    repos = [Path(item) for item in (args.repo or ["."])]
    while True:
        failed = False
        for repo in repos:
            try:
                mirror(repo, args.source, args.target, dry_run=args.dry_run)
            except MirrorError as error:
                failed = True
                print(f"mirror {repo}: {error}", file=sys.stderr)
        if not args.loop:
            return 1 if failed else 0
        time.sleep(max(args.interval, 10))


if __name__ == "__main__":
    raise SystemExit(main())
