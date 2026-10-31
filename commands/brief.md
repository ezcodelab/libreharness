---
description: One-page task brief from the queue, project rules, and lessons
---
<!-- SPDX-License-Identifier: MIT -->
Build a one-page brief for task: $ARGUMENTS

Use the work-queue and engineering-loop skills.

1. Read the task packet:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" show <id> --packet`.
   If there is no task, say so and use the stated scope.
2. Read the project `AGENTS.md`, `docs/INDEX.md` when present, and the files or
   tests the task names. Do not read the whole repository.
3. Find up to three matching lessons in the project's
   `docs/process-lessons.md`. Include only lessons that change the next action.
4. List the skills under `${HARNESS_HOME}/skills/*/SKILL.md` and name at most
   two that apply.
5. Output, in this order:
   - **Task** and one-sentence scope
   - **Out of scope**
   - **Acceptance** as observable checks
   - **Invariants** and trust boundaries
   - **Risks / unknowns**
   - **Definition of done** (the quality axes that matter here)
   - **Past lessons** (0 to 3, with why each applies)
   - **First action** and the exact check that proves it
6. Stop. Do not edit code in this turn.
