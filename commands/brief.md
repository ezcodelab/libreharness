---
description: One-page task brief from the queue, project rules, and lessons
---
<!-- SPDX-License-Identifier: MIT -->
Build a one-page brief for task: $ARGUMENTS

Use the work-queue and engineering-loop skills.

1. Read the task packet:
   `tasks show <id> --packet`.
   If there is no task, say so and use the stated scope.
2. Read the project `AGENTS.md`, `CONTRIBUTING.md`, and the files or tests the
   task names. Do not read the whole repository.
3. Find the matching lessons in the project's `docs/process-lessons.md`.
   Include only lessons that change the next action.
4. List the injected skills and name the skills that apply.
5. Output, in this order:
   - **Task** and one-sentence scope
   - **Playbook**: the `engineering-loop` row that matches, or the fallback and why
   - **Out of scope**
   - **Data shape**: the types, the state machine, the boundary parser, and which
     structure owns each piece of state
   - **Acceptance** as observable checks. For a goal with children, shape each
     one with `skills/goal/references/spec-shape.md`.
   - **Reach**: callers, importers, tests, fixtures, config, exports, and
     wire-format consumers the change must touch or preserve
   - **Invariants** and trust boundaries
   - **Risks / unknowns**
   - **Definition of done** (the quality axes that matter here)
   - **Past lessons** (0 to 3, with why each applies)
   - **First action** and the exact check that proves it
6. Write two lines into the task `## Plan` before input:
   - `Data shape:` one non-empty JSON object or array, or
     `path <repo-relative-file>#<symbol>`, or `none - <reason>` only for a
     `docs` or `chore` task;
   - `Verify:` one command from the review allowlist. A product task that cannot
     name its real check stays unverified; do not point Verify at a harness check.
7. Stop. Do not edit code in this turn.
