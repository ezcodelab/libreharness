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
2. Run the final `/review` if the task has a diff. Record the verdict.
3. If Jev is configured, run the advisory close triage:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/jev_triage.py" --state /tmp/opencode/close-state-<id>.txt --json`
   - exit 4: say the configured model is gone; do not silently switch to paid.
   - exit 3: note "Jev unavailable" and use your own judgment.
   - Jev never blocks the close by itself.
4. Append exactly one dated entry to the project's `docs/process-lessons.md`:
   - Surprise
   - Cost
   - Rule
   - Doc updated
   - `Promote-to-global` when portable
   If nothing surprised you, write "Surprise: none" rather than inventing one.
5. If the project has a skill candidate, put it in the task evidence or the
   project's skill directory. Do not promote it to global in this turn. `/tune`
   and `docs/skill-eval.md` handle promotion.
6. Update the queue with the evidence:
   `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py" status <id> done --evidence "<command and result>"`.
7. Show what passed, what remains unproven, and the next action. Stop.
