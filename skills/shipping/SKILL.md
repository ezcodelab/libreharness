---
name: shipping
description: Open a ready pull request, validate the review artifact and required CI on the exact head, and merge only that head. Use after review or when a task is ready to land.
---
<!-- SPDX-License-Identifier: MIT -->

# Shipping

Use after the task is `review` or `done`, the diff is reviewed, and the review
artifact is PASS. The goal is one verified PR through the forge, not a direct
push.

## Resolve the forge once

1. Public repos (Credarr, LibreHarness): `gh`; GitHub is canonical and Gitea is
   a read-only mirror.
2. Gitea-canonical repos (Brain and the homelab repos): push an AGit PR to
   `refs/for/main/<topic>`. The repository gate schedules the merge after CI;
   no agent token is needed.
3. If no forge path resolves, stop with the exact command and the missing
   capability. Do not claim the work merged.

Never install a CLI silently, put a token in argv or output, require both forges,
push to `main`, or force-push a shared branch.

## Auto-merge is the default

Once the review artifact and required checks pass, merge in the same task. Do not
ask the operator to merge a green, reviewed PR or leave it open as "ready for
review"; an unmerged reviewed patch is unfinished work.

## Required gates

- The task has scope, observable acceptance, and recorded evidence.
- The review artifact is PASS for the exact head, includes the task's Verify
  command, and every recorded exit is zero.
- Deterministic checks pass on the exact head: tests, Markdown, links, secrets,
  and the repository's other required checks.
- CI is green on that head, with no pending or skipped required check.
- The PR is ready, mergeable, conflict-free, and has no secrets.
- Any repository human gate, such as required reviews or a ruleset, is satisfied.

A green CI is not a review. A failed gate is a stop, not a reason to weaken it.

## 1. Prepare the patch

Work from the lane branch or a fresh branch off current trunk. Rebase only your
own branch. Keep the diff small; prefer narrow PRs to one large PR. Commit with
`-s`, and run the project checks before the first push and after any change that
invalidates them.

## 2. Validate the review artifact

Before opening the PR, and again after any new commit, validate the artifact on
the tree that will land:

```sh
python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" review <id> --repo "$PWD"
```

A missing, stale, failed, mismatched, or UNVERIFIED artifact blocks. Record a new
one with the task's Verify command when the head moves.

## 3. Open the PR ready

Never open a draft. Use a one-minute briefing for a reviewer who has the diff:

- `## Why`: the problem and approach.
- `## What changed`: short bullets naming real symbols or paths.
- `## Scope`: what this covers and deliberately leaves out.
- `## Tradeoffs`: only rejected alternatives worth asking about.
- `## Blast Radius`: who or what it touches and why that is safe.
- `## Verification`: the real commands, observed exits, and artifact path.

Open it with `gh pr create` and keep the URL.

## 4. Watch CI and merge

Pin the head, wait for every required check, then merge the exact commit:

```sh
HEAD=$(gh pr view <number> --json headRefOid --jq .headRefOid)
gh pr checks <number> --watch --required --interval 20
gh pr merge <number> --squash --match-head-commit "$HEAD" --delete-branch
```

If the artifact head and `$HEAD` differ, stop and re-record. If a required check
is missing, pending, skipped, or failed, stop.

For a Gitea-canonical repo, push the AGit PR and let the repository gate merge it,
with no token polling.

## 5. After the merge

Re-read the PR and confirm it is merged, not merely queued. Delete only the
branch you created, after its worktree is gone. Update the task with the PR URL
and merge commit. A queued or blocked merge is reported as that state, not as
landed.

## Stop conditions

Stop and report instead of merging when:

- the forge is unavailable or does not resolve the repository;
- the review artifact is missing, failed, stale, or for a different head;
- CI is pending, failed, skipped, or absent;
- the PR has conflicts, is a draft, or is not mergeable;
- a repository human gate is unsatisfied;
- evidence is missing or the diff contains a secret;
- the next action is irreversible: production deploy, data deletion, force-push,
  live secret rotation, or an external message. Stop and name the exact action.

Do not disable a required check or merge on a stale artifact.
