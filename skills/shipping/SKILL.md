---
name: shipping
description: Open a ready pull request, wait for CI, obtain an independent verifier PASS, and merge only the verified patch. Use after review or when a task is ready to land.
---
<!-- SPDX-License-Identifier: MIT -->

# Shipping

Use after the task is `review` or `done`, the diff is reviewed, and the evidence
exists. The goal is one verified PR through the forge, not a direct push.

## Resolve the forge once

1. `gh` when it exists and resolves the repository. Public repos are GitHub canonical; Gitea is a read-only mirror.
2. Private Gitea repos when `GITEA_TOKEN` is set: `--forge gitea --repo OWNER/REPO`; see the command reference.
3. Manual fallback: print the exact PR and merge commands and stop. Do not claim
   the work merged.

Record the forge. Never install a CLI silently or put a token in argv/output.
Never require both forges; never push to `main` or force-push a shared branch.

## Required gates

- The task has scope, observable acceptance, and recorded evidence.
- Deterministic checks pass on the exact head: tests, docs lint, SPDX,
  private-path scan, diff check, and the repository secret scan.
- A fresh verification artifact exists: a real user path, a formal/property
  check, or a named test. A unit test alone is not enough for user-visible
  behavior.
- An independent verifier that did not write the code returns `PASS` or
  `PASS+NOTES` for the current head.
- CI is green on that head, with no pending or skipped required check.
- The PR is ready, mergeable, conflict-free, and has no secrets.

A green CI is not a verdict. A failed gate is a stop, not a reason to weaken it.

## 1. Prepare the patch

Work from the lane branch or a fresh branch off the current trunk. Rebase only
your own branch. Keep the diff small; prefer five narrow PRs to one large PR.
Commit with `-s`. Run the project checks before the first push and again after
any change that invalidates them.

## 2. Open the PR ready

Never open a draft. Use a one-minute briefing for a reviewer who has the diff:

- `## Why`: the problem and approach.
- `## What changed`: short bullets naming real symbols or paths.
- `## Scope`: what this covers and deliberately leaves out.
- `## Tradeoffs`: only rejected alternatives worth asking about.
- `## Blast Radius`: who or what it touches and why that is safe.
- `## Verification`: the real commands and results.

Open it with `gh pr create` or the Gitea UI/API. Keep the URL.

## 3. Independent verification

The author does not verify its own patch. Use a fresh context: `devils-advocate`,
a second reviewer, or the verification skill. It must run the real artifact or
the named formal check, not just read the diff.

Write the verdict to a file with the PR head SHA:

```text
PASS <40-character-head-sha>
```

Use `PASS+NOTES <sha>` when it passes with non-blocking notes. A `FAIL`, a
missing SHA, or a stale SHA blocks the merge.

## 4. Watch CI and merge

Run the gate:

```sh
python3 bin/pr_watch.py --pr <number> \
  --verifier-pass <verdict-file> --evidence <task-evidence-file> --wait 900
```

Omit `--required-check` to require every check green. If you pass it, use the
exact check-run name; matrix jobs are named like `test (3.10, 20)`, not `test`.
Add `--repo OWNER/REPO` when the checkout cannot infer it. The script prints
every failing gate and exits non-zero. It does not merge in dry-run mode.

For private Gitea repos, push an AGit PR; the auto-merge workflow schedules after CI. Use `pr_watch` only for bootstrap/protected changes with an operator token:

```sh
python3 bin/pr_watch.py --forge gitea --repo OWNER/REPO --pr <number> \
  --verifier-pass <file> --evidence <file> \
  --required-check "CI / check (pull_request)" --auto
```

Set `GITEA_URL` and `GITEA_TOKEN` in the operator environment; never put the token in argv/output.
`--auto` schedules Gitea `merge_when_checks_succeed` at the verified head.
Use `--merge` instead to merge immediately after the gate; GitHub always uses
`--merge`. Both pin the head (`--match-head-commit` or `head_commit_id`), so a
moved head is refused. Only the verified patch on green CI merges.

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
- the change touches a human-only gate: secrets, production, release, auth,
  data migration, branch protection, or an operator-owned decision.

Do not bypass branch protection, disable a check, or merge on a stale verdict.
