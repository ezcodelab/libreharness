<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Gitea read-only mirror

GitHub is canonical for **Credarr** and **LibreHarness**. Gitea is a read-only
pull mirror for private homelab/agent access and backup. It is not a
contribution surface and never pushes to GitHub.

## Direction

```text
GitHub main/tags  ->  Gitea mirror
```

The mirror is one-way. GitHub PRs merge on GitHub; Gitea catches up on the
mirror interval. Gitea does not accept PRs for these repositories and does not
push branches or tags back to GitHub.

## Setup

The old Gitea repositories are archived as `*-gitea-archive` so their PR and
issue history stays readable. The canonical Gitea names are then created as
pull mirrors:

- source: `https://github.com/ezcodelab/<repo>.git`
- interval: 10 minutes
- code and tags only; no issues, pull requests, or releases
- read-only: no pushes, no PRs, no merges

Gitea's built-in mirror owns the sync. There is no local outbound mirror job
and no bidirectional sync.

## Why not bidirectional

A two-way mirror diverges on squash, rebase, and merge commits, and leaves two
competing merge gates. The rule is one canonical branch per repository:
GitHub for public repos, Gitea for private/agent-only repos.

## Local remotes

`origin` is GitHub; `gitea` is the read-only mirror. Run
`git config core.hooksPath .githooks` once per clone. The pre-push hook rejects
pushes to `gitea` with a clear message.

## Freshness check

`bin/check_mirror.py` compares each Gitea mirror's `main` with GitHub `main`.
It is tokenless by default; set `GITHUB_TOKEN` or `GITEA_TOKEN` only if an API
requires authentication.

```sh
python3 bin/check_mirror.py \
  --pair ezcodelab/libreharness=admin/libreharness \
  --pair ezcodelab/credarr=admin/credarr \
  --gitea-api https://git.ezcloud.casa/api/v1 --max-age 1200
```

If the SHAs match, the mirror is fresh. If the mirror is behind, the GitHub
`main` commit age is the grace clock: a commit newer than 1200 seconds is
within the 10-minute mirror interval, and an older commit is stale. Exit codes
are `0` fresh/within grace, `1` stale, and `2` API error. The systemd user
check runs every five minutes; its `OnFailure` alert unit writes a `user.err`
journal entry.

## Retired scoped source

Remove the old owner-level scoped workflow source registration in
**User Settings -> Actions -> Scoped Workflows**. The source repository is now
`admin/libreharness-gitea-archive`; the registration is inert and should not be
reused.

## History

The outbound Gitea-to-GitHub mirror, its systemd units, and its lock/status
machinery were removed when the public repos flipped to GitHub canonical. The
archived Gitea repos retain the old history.
