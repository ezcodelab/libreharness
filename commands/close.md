---
description: Close a task with final review, optional Jev triage, lessons, and queue evidence
---
<!-- SPDX-License-Identifier: MIT -->
Close task: $ARGUMENTS

Use the work-queue and engineering-loop skills. Do not edit feature code in this
turn.

1. Read the task packet:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" show <id> --packet`.
   Confirm every acceptance item and its evidence. Missing evidence means the
   task stays active.
2. If the task is a goal with child lanes, run `/integrate` for the reviewed
   lanes first. For a single task, skip this step.
3. Run the final `/review` if the task has a diff. Record the verdict.
4. If Jev is configured, run the advisory close triage:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/jev_triage.py" --state /tmp/opencode/close-state-<id>.txt --json`
   - exit 4: say the configured model is gone; do not silently switch to paid.
   - exit 3: note "Jev unavailable" and use your own judgment.
   - Jev never blocks the close by itself.
5. Append exactly one dated entry to the project's `docs/process-lessons.md`:
   - Surprise
   - Cost
   - Rule
   - Doc updated
   - `Promote-to-global` when portable
   If nothing surprised you, write "Surprise: none" rather than inventing one.
   If the lesson is a repeated correction, apply it at the highest level that
   works: architecture, then types, then a lint whose error names the fix, then
   a test, and docs last. Prove the check fails on the past mistake. Do not add
   a new command when `/close` or `/tune` can own the rule.
6. If the project has a skill candidate, put it in the task evidence or the
   project's skill directory. Do not promote it to global in this turn. `/tune`
   and `docs/skill-eval.md` handle promotion.
7. Update the queue with the evidence:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" status <id> done --evidence "<command and result>"`.
8. Show what passed, what remains unproven, and the next action. Stop.
