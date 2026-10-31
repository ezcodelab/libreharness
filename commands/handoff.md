---
description: Write a budgeted handoff for a paused or finished task
---
<!-- SPDX-License-Identifier: MIT -->
Handoff: $ARGUMENTS

Use the handoff section in `engineering-loop`; the format is below. Do not edit code.

1. Require a task id. Read the task packet and the current task file.
2. Write or replace the task's `## Handoff` section with exactly:
   - **State:** done / in progress / blocked by ...
   - **Decisions:** the choice and why; link the decision record
   - **Files:** paths changed, and the one or two that matter most
   - **Checks:** command, result, timestamp; “not run” is valid
   - **Open:** unresolved questions, risks, and what would change the plan
   - **Next:** one bounded next action, with the command or file
   - **Context:** links to the task, index section, lesson, and review
3. Keep it under 40 lines. No secrets, tokens, values, full logs, or
   transcript. Cite paths and shapes.
4. Save it with `tasks.py handoff <id> --file /tmp/opencode/handoff-<id>.md`
   (write the file first) or with the edit tool. Then run `tasks.py validate` and show
   the handoff. Stop; do not close the task unless `/close` was also requested.
