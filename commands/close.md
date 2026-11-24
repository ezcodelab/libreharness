---
description: Finish a task or goal: validate the review artifact, integrate lanes, reap worktrees, evidence
---
<!-- SPDX-License-Identifier: MIT -->
Close: $ARGUMENTS

Use the work-queue and engineering-loop skills. This is the only finish command.
Do not edit feature code in this turn.

1. Read the task packet:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" show <id> --packet`.
   Confirm every acceptance item and its evidence. Missing evidence means the
   task stays open. Converge: compare every acceptance item and named
   requirement with the code on the tree that will land. A completion claim
   without evidence is open work. Append unmet work as a follow-up task or
   child; never rewrite the scope to match what was built.
2. If the task is a goal, run `goal-status <id>`. If it is not closable, stop
   and list the unfinished children; finish them with a follow-up goal or child,
   then run `/close` again. For a single task, skip this step.
3. If the task has lanes (a goal with child lanes, or a single task with a
   worktree), integrate:
   - read the child packets, or the single task packet, and refuse anything
     that is not `review`/`done`, has no Evidence, or has a failing review
     artifact;
   - build the merge map from branch, base, owns, and merge order; stop if two
     children claim the same file or interface;
   - ship each independently shippable child as its own small PR off trunk;
     stack only a child that needs the code below it, and land the stack
     bottom-up. For a single task, ship its branch as one PR from its base;
   - create a combined integration branch only when a cross-lane acceptance
     cannot be proved on trunk. Split that combined work by review boundary;
     never merge independent lanes into one large PR;
   - stop on a conflict and leave the tree resumable;
   - run the full project check on current trunk after child PRs land.
   Do not create a separate integration task or command; this is part of close.
4. First gate: validate the review artifact on the tree that will land:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" review <id> --repo "$PWD"`.
   A missing, stale, failed, mismatched, or UNVERIFIED artifact stops the close.
   Integration or any commit or working-tree change makes the artifact stale; record a new PASS
   with the task's Verify command before continuing.
5. Run the final `/review` on the merged diff, or on the single task's diff.
   A send-back stops the close. Fix empirical failures and rerun the acceptance
   check; there is no second abstract pass.
   Reuse the recorded review without another abstract pass only when all hold:
   the task is a single task in `review`, no integration occurred, and the
   artifact validates for the same HEAD and diff fingerprint. Any new commit,
   working-tree change, acceptance change, or new finding requires the full
   review. State which path you took.
6. If a single task still has a worktree and is `active`, move it to `review`
   now (`tasks.py status <id> review --note "final review passed" --repo "$PWD"`)
   so the reaper can evaluate it. The status gate revalidates the artifact.
   Goal children are already final.
7. Reap clean lanes:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" reap <id>`
   It removes only clean worktrees, with no ignored files, whose branch is merged
   into another branch.
   If it exits non-zero, stop and leave the task or goal open; report every
   retained lane (active, dirty, or unmerged) and the exact next action.
8. If the work repeated a correction, use the `correct` skill: fix it at the
   highest level that works, prove the check fails on the past mistake, and
   append the rule to `skills/correct/references/rule-ledger.md`. Do not invent a
   lesson when nothing surprised you.
9. Update the queue with evidence that names the unit fail and pass commands,
   the smoke JSON path when one exists, and the review artifact path:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" status <id> done --evidence "<commands and results>"`.
10. If the task is mergeable and a forge is configured, use the `shipping`
    skill. Open one ready PR that one reviewer can review in one sitting, with
    a `type(scope): subject` title and the required body headings. Stay active
    until `bin/pr_guard.py land` merges the exact reviewed head, or one
    actionable blocker is recorded. Fix CI, rebase your own branch, or close a
    superseded PR; do not leave an open ready PR for the operator to finish. If
    no forge resolves, print the manual PR and merge commands and stop. Never
    push directly to main.
11. Show what passed, what remains unproven, the PR state, and the next action.
    Stop.
