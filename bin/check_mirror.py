#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare a Gitea read-only mirror with GitHub main.

The check is tokenless by default: GitHub and the Gitea mirror are public. Set
GITHUB_TOKEN or GITEA_TOKEN only if the API needs authentication. A mirror is
fresh when main matches. If it is behind, the GitHub main commit age is the
grace clock: a commit newer than --max-age is still within the mirror interval;
an older commit means the mirror is stale.
"""

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


class CheckError(RuntimeError):
    pass


def fetch_json(url, token, scheme, insecure):
    headers = {
        "Accept": "application/json",
        "User-Agent": "libreharness-mirror-check",
    }
    if token:
        headers["Authorization"] = f"{scheme} {token}"
    kwargs = {"timeout": 30}
    if insecure:
        kwargs["context"] = ssl._create_unverified_context()
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, **kwargs) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise CheckError(f"HTTP {error.code} for {url}") from None
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
        raise CheckError(f"{error} for {url}") from None


def parse_pair(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "pair must be GITHUB_OWNER/REPO=GITEA_OWNER/REPO"
        )
    github, gitea = value.split("=", 1)
    github = github.strip()
    gitea = gitea.strip()
    if "/" not in github or "/" not in gitea:
        raise argparse.ArgumentTypeError(
            "pair must be GITHUB_OWNER/REPO=GITEA_OWNER/REPO"
        )
    return github, gitea


def github_main(api, repo, token, insecure):
    data = fetch_json(
        f"{api.rstrip('/')}/repos/{repo}/commits/main",
        token,
        "Bearer",
        insecure,
    )
    sha = str(data.get("sha") or "")
    commit = data.get("commit") or {}
    date = str(
        (commit.get("committer") or {}).get("date")
        or (commit.get("author") or {}).get("date")
        or ""
    )
    if not sha or not date:
        raise CheckError(f"GitHub main metadata is incomplete for {repo}")
    return sha, date


def gitea_main(api, repo, token, insecure):
    data = fetch_json(
        f"{api.rstrip('/')}/repos/{repo}/branches/main",
        token,
        "token",
        insecure,
    )
    sha = str((data.get("commit") or {}).get("id") or "")
    if not sha:
        raise CheckError(f"Gitea main metadata is incomplete for {repo}")
    return sha


def age_seconds(date):
    try:
        moment = datetime.fromisoformat(date.replace("Z", "+00:00"))
    except ValueError:
        raise CheckError(f"invalid GitHub commit date: {date}") from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - moment).total_seconds())


def check_pair(
    pair,
    max_age,
    github_api,
    gitea_api,
    github_token,
    gitea_token,
    insecure,
):
    github, gitea = pair
    github_sha, github_date = github_main(
        github_api, github, github_token, insecure
    )
    gitea_sha = gitea_main(gitea_api, gitea, gitea_token, insecure)
    result = {
        "github": github,
        "gitea": gitea,
        "github_sha": github_sha,
        "gitea_sha": gitea_sha,
        "ok": True,
        "age_seconds": 0,
        "detail": "in sync",
    }
    if github_sha == gitea_sha:
        return result
    age = age_seconds(github_date)
    result["age_seconds"] = round(age, 3)
    if age > max_age:
        result["ok"] = False
        result["detail"] = (
            f"Gitea main {gitea_sha[:12]} is behind GitHub "
            f"{github_sha[:12]}; GitHub commit is {int(age)}s old "
            f"(limit {max_age}s)"
        )
    else:
        result["detail"] = (
            f"mirror behind by a new commit ({int(age)}s old); "
            f"within {max_age}s grace"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        action="append",
        type=parse_pair,
        required=True,
        help="GITHUB_OWNER/REPO=GITEA_OWNER/REPO; repeatable",
    )
    parser.add_argument("--max-age", type=int, default=1200)
    parser.add_argument(
        "--github-api",
        default=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
    )
    parser.add_argument(
        "--gitea-api",
        default=os.environ.get("GITEA_URL", ""),
        help="Gitea API base; defaults to GITEA_URL",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="skip Gitea TLS verification",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.gitea_api:
        print(
            "check_mirror: --gitea-api or GITEA_URL is required",
            file=sys.stderr,
        )
        return 2

    github_token = os.environ.get("GITHUB_TOKEN", "")
    gitea_token = os.environ.get("GITEA_TOKEN", "")
    results = []
    errors = []
    for pair in args.pair:
        try:
            result = check_pair(
                pair,
                args.max_age,
                args.github_api,
                args.gitea_api,
                github_token,
                gitea_token,
                args.insecure,
            )
        except CheckError as error:
            errors.append(f"{pair[0]}={pair[1]}: {error}")
            results.append(
                {
                    "github": pair[0],
                    "gitea": pair[1],
                    "ok": False,
                    "detail": str(error),
                }
            )
            continue
        results.append(result)
        print(
            f"mirror {'OK' if result['ok'] else 'FAIL'} "
            f"{pair[0]} -> {pair[1]}: {result['detail']}"
        )

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not errors
                    and all(item["ok"] for item in results),
                    "max_age": args.max_age,
                    "pairs": results,
                },
                indent=2,
            )
        )
    for error in errors:
        print(f"check_mirror: {error}", file=sys.stderr)
    if errors:
        return 2
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
