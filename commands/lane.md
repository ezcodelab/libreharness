---
description: Create one isolated worktree lane for a queued task
---
<!-- SPDX-License-Identifier: MIT -->
Lane: $ARGUMENTS

Use the parallel-lanes and work-queue skills. Do not edit code in this turn.

1. Require a task id. If missing, ask for it or list `tasks.py ready`.
2. Run `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" show <id> --packet`
   and verify the task is `ready`/`inbox`, has no open dependencies, and has a
   scope and acceptance checks. If not, stop with the missing item.
3. Infer the repo from the current directory. Create the lane with:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" lane <id> --repo <repo> --owner <lane-name> [--name <short>] [--base <branch>] [--setup "<command>"]`
   The default is `<repo-parent>/<repo>-<name>`, branch `feature/<name>`.
   If the operator already created an OpenCode worktree, do not create a second
   one: claim the task with
   `--worktree <path> --branch <branch> --base <base> --owner <lane>` so
   `/review` can diff the committed lane against its base.
4. Output a worker packet, not a plan essay:
   - **Task / lane / branch / worktree**
   - **Owns:** files and interfaces this lane may change
   - **Does not touch:** shared config, state files, other lanes' files
   - **Acceptance:** the task's checks
   - **Run:** the project's test/lint command
   - **Before pause/review:** `/handoff <id>` then `/review <id>`
5. Stop. The lane owner does the implementation.
