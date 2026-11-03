---
description: Finish a task or goal: integrate lanes, final review, reap worktrees, lesson, evidence
---
<!-- SPDX-License-Identifier: MIT -->
Close: $ARGUMENTS

Use the work-queue and engineering-loop skills. This is the only finish command.
Do not edit feature code in this turn.

1. Read the task packet:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" show <id> --packet`.
   Confirm every acceptance item and its evidence. Missing evidence means the
   task stays open.
2. If the task is a goal, run `goal-status <id>`. If it is not closable, stop
   and list the unfinished children; finish them with a follow-up goal or child,
   then run `/close` again. For a single task, skip this step.
3. If the task has lanes (a goal with child lanes, or a single task with a
   worktree), integrate:
   - read the child packets, or the single task packet, and refuse anything
     that is not `review`/`done`, has no Evidence, or has a failing review;
   - build the merge map from branch, base, owns, and merge order; stop if two
     children claim the same file or interface;
   - merge in the declared order into one integration branch; for a single
     task, create that branch from its base and merge its branch into it. Keep
     the work off main until the operator ships;
   - stop on a conflict and leave the tree resumable;
   - run the full project check on the merged tree.
   Do not create a separate integration task or command; this is part of close.
4. Run the final `/review` on the merged diff, or on the single task's diff.
   Record the verdict. A send-back stops the close.
5. If a single task still has a worktree and is `active`, move it to `review`
   now (`tasks.py status <id> review --note "final review passed"`) so the
   reaper can evaluate it. Goal children are already final.
6. Reap clean lanes:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" reap <id>`
   It removes only clean worktrees, with no ignored files, whose branch is merged
   into another branch.
   If it exits non-zero, stop and leave the task or goal open; report every
   retained lane (active, dirty, or unmerged) and the exact next action.
7. If Jev is configured, run the advisory close triage:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/jev_triage.py" --state /tmp/opencode/close-state-<id>.txt --json`
   - exit 4: say the configured model is gone; do not silently switch to paid.
   - exit 3: note "Jev unavailable" and use your own judgment.
   - Jev never blocks the close by itself.
8. Append exactly one dated entry to the project's `docs/process-lessons.md`:
   - Surprise
   - Cost
   - Rule
   - Doc updated
   - `Promote-to-global` when portable
   If nothing surprised you, write "Surprise: none" rather than inventing one.
   If the lesson is a repeated correction, apply it at the highest level that
   works: architecture, then types, then a lint whose error names the fix, then
   a test, and docs last. Prove the check fails on the past mistake.
9. If the project has a skill candidate, put it in the task evidence or the
   project's skill directory. Do not promote it to global in this turn. `/tune`
   and `docs/skill-eval.md` handle promotion.
10. Update the queue with the evidence:
    `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" status <id> done --evidence "<command and result>"`.
11. Show what passed, what remains unproven, and the next action. Stop.
