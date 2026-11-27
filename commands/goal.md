---
description: Manual task entry: execute a small task, or plan and run a multi-step goal
---
<!-- SPDX-License-Identifier: MIT -->
Request: $ARGUMENTS

Use the `goal`, `work-queue`, `parallel-lanes`, and `engineering-loop` skills.
This is an escape hatch; auto-intake handles a normal request without a command.

1. If `$ARGUMENTS` is an existing task or goal id, read its packet. For a goal,
   call `tasks` with `goal-status`, then `goal-start`. Execute each ready child
   with the `work-queue` brief, implement, the `review` command, and the `close`
   command. Use `tasks lane` only when the operator explicitly wants a manual
   worktree.
2. If it is a new request, brief it with the `work-queue` brief reference. Plan
   it with the `goal` skill, show the plan, and stop for approval before
   creating it.
3. Let the `goal` skill own the plan, child, dependency, and lane details. Do
   not restate or improvise them here.
