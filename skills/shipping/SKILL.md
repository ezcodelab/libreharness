---
name: shipping
description: Open a ready pull request, wait for CI, obtain an independent verifier PASS, and merge only the verified patch. Use after review or when a task is ready to land.
---
<!-- SPDX-License-Identifier: MIT -->

# Shipping

Use after the task is `review` or `done`, the diff is reviewed, and evidence
exists. The goal is one verified PR through the forge, not a direct push.

## Resolve the forge once

1. Public repos (Credarr, LibreHarness): `gh`; GitHub is canonical and Gitea is
   a read-only mirror.
2. Gitea-canonical repos (Brain and the homelab repos): push an AGit PR to
   `refs/for/main/<topic>`. The repository gate schedules the merge after CI;
   no agent token is needed.
3. If no forge path resolves, stop with the exact command and the missing
   capability. Do not claim the work merged.

Never install a CLI silently, put a token in argv or output, require both
forges, push to `main`, or force-push a shared branch.

## Auto-merge is the default

Once the required checks and the independent verdict pass, merge in the same
task. Do not ask the operator to merge a green, reviewed PR or leave it open as
"ready for review"; an unmerged reviewed patch is unfinished work. The exception
is a gate, CI, auth, deploy, or release change: it still gets the verdict, then
stops at merge-ready because the gate cannot certify its own weakening.

A gate-only failure is one decision, not an indefinite open PR. Ask the operator
once in the same turn with the exact `--admin --match-head-commit` command. If
authorized, merge that head now. If declined, close the PR with the reason.
Never end a task with a reviewed PR open.

## Required gates

- The task has scope, observable acceptance, and recorded evidence.
- Deterministic checks pass on the exact head: tests, Markdown, links, secrets,
  and the repository's other required checks.
- A fresh verification artifact exists: a real user path, a formal or property
  check, or a named test. A unit test alone is not enough for user-visible
  behavior.
- An independent verifier that did not write the code returns `PASS` or
  `PASS+NOTES` for the current head.
- CI is green on that head, with no pending or skipped required check.
- The PR is ready, mergeable, conflict-free, and has no secrets.

A green CI is not a verdict. A failed gate is a stop, not a reason to weaken it.

## 1. Prepare the patch

Work from the lane branch or a fresh branch off current trunk. Rebase only your
own branch. Keep the diff small; prefer narrow PRs to one large PR. Commit with
`-s`, and run the project checks before the first push and after any change that
invalidates them.

## 2. Open the PR ready

Never open a draft. Use a one-minute briefing for a reviewer who has the diff:

- `## Why`: the problem and approach.
- `## What changed`: short bullets naming real symbols or paths.
- `## Scope`: what this covers and deliberately leaves out.
- `## Tradeoffs`: only rejected alternatives worth asking about.
- `## Blast Radius`: who or what it touches and why that is safe.
- `## Verification`: the real commands and results.

Open it with `gh pr create` and keep the URL.

## 3. Independent verification

The author does not verify its own patch. Use a fresh context: `devils-advocate`,
a second reviewer, or the verification skill. It must run the real artifact or
named formal check, not just read the diff.

Write the verdict to a file with the PR head SHA:

```text
PASS <40-character-head-sha>
```

Use `PASS+NOTES <sha>` when it passes with non-blocking notes. A `FAIL`, a
missing SHA, or a stale SHA blocks the merge.

## 4. Watch CI and merge

Pin the head, wait for every required check, then merge the exact commit:

```sh
HEAD=$(gh pr view <number> --json headRefOid --jq .headRefOid)
gh pr checks <number> --watch --required --interval 20
gh pr merge <number> --squash --match-head-commit "$HEAD" --delete-branch
```

If the verifier's SHA and `$HEAD` differ, stop and re-verify. If a required
check is missing, pending, skipped, or failed, stop.

For a Gitea-canonical repo, push the AGit PR and let the repository gate merge
it. Do not poll with a token.

## 5. After the merge

Re-read the PR and confirm it is merged, not merely queued. Delete only the
branch you created, after its worktree is gone. Update the task with the PR URL
and merge commit. If the merge is queued or blocked, report that state; do not
say it landed.

## Stop conditions

Stop and report instead of merging when:

- the forge is unavailable or does not resolve the repository;
- the verifier is missing, failed, or verified a different head;
- CI is pending, failed, skipped, or absent;
- the PR has conflicts, is a draft, or is not mergeable;
- evidence is missing or the diff contains a secret;
- the change touches a human-only gate: secrets, production, release, auth, data
  migration, branch protection, CI, or an operator decision. Stop at merge-ready,
  name the exact merge, and do not leave a silent open PR.

Do not bypass branch protection, disable a check, or merge on a stale verdict.
