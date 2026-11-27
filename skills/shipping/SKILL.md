---
name: shipping
description: Open one ready PR, validate the review artifact and required CI on the exact head, and stay until it merges. Use after review or when a task is ready to land.
---
<!-- SPDX-License-Identifier: MIT -->

# Shipping

Ship one small verified PR, then confirm it merged. Opening a PR is not the end
of the task, and a ready PR left for the operator is unfinished work.

## Forge

Use `gh` for GitHub-canonical repositories. For Gitea-canonical repositories,
push an AGit PR to `refs/for/main/<topic>` and let the repository gate merge it.
If no forge resolves, stop with the exact manual command. Never require both,
push to `main`, force-push a shared branch, or install a CLI silently.

## Gates

- Task scope, acceptance, and evidence are recorded.
- Review artifact is PASS for the exact head, includes Verify, and every exit is
  zero.
- PR is one logical change, reviewable in one sitting, with the required title
  and body headings. Split when a reviewer cannot review it in one pass; never
  split by an arbitrary number.
- Title is `type(scope): subject`.
- Body has `Why`, `What changed`, `Scope`, optional `Tradeoffs`, `Blast Radius`,
  and `Verification`, in order.
- Required CI is green on the exact head, the PR is ready and mergeable, and
  repository human gates are satisfied.

## 1. Open

Work from a lane worktree or a fresh branch off trunk. Keep unrelated work out.
Group changes into small verifiable commits. One task gets one PR.

Independent changes branch off trunk and land as separate PRs. Stack only a
dependent follow-up, one PR per review unit, and land bottom-up. A cleanup,
refactor, docs change, or separate capability gets its own PR when it can land
alone. Split by behavior and review boundary, not file count. If a split grows
into many follow-ups, split the task before opening anything.

Write the body first, then call `pr_guard` with
`args: ["check", "--base", "main", "--title", "<title>", "--body-file", "<os-temp>/pr-body.md"]`.

It must return `"ok": true` and `"next": "open"` on a clean committed head.
Commit with `-s` and run the project checks before the first push and after any
invalidating change.

Validate the artifact on the tree that will land: call `tasks` with
`args: ["review", "<id>"]`.

Then open the PR ready. Never open a draft. Keep the URL.

## 2. Land

Pin the head, then call `pr_guard` in the foreground with a timeout long enough
for CI and act on its JSON:

```sh
HEAD=$(gh pr view <number> --json headRefOid --jq .headRefOid)
```

`pr_guard` args: `["land", "--pr", "<number>", "--head", "$HEAD", "--base", "main"]`.

- `fix`: fix the failed required check, commit, record a new artifact, push, and
  run `land` again. Classify it first with `references/ci-failure-classes.md`; a
  rerun without a change is not a fix.
- `rebase`: rebase only this PR's branch with `--force-with-lease`, record a new
  artifact, push, and run `land` again.
- `rereview`: the head moved. Record the artifact before merging.
- `wait`: the forge has not settled. Read the PR again; do not claim a merge.

Do not start `land` in the background and end the turn. If a required check
fails twice on the same axis or a human gate blocks, stop with that one blocker
and the exact next action. Do not open another PR for the same task.

## 3. Confirm

Read the PR after merge: state `MERGED`, merge commit, and the reviewed head.
Delete only the branch you created after its worktree is gone. Update the task
with the PR URL and merge commit.

## Stop

Stop only for an unavailable forge, a missing or stale artifact, a malformed PR,
failed required checks after two same-axis fixes, a conflict you cannot resolve
on your own branch, an unsatisfied human gate, a secret, or an irreversible
action. A queued or pending result is not merged.
