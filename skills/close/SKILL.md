---
name: close
description: Finish a task or goal by validating the review artifact, integrating lanes, reaping worktrees, recording evidence, and shipping a reviewed pull request.
---
<!-- SPDX-License-Identifier: MIT -->

# Close gate

Close the task or goal supplied with this invocation.

Use the `work-queue`, `shipping`, and `engineering-loop` skills. This is the only
finish step. Do not edit feature code in this turn.

1. Read the task packet and confirm every acceptance item against evidence on the
   tree that will land. Missing evidence keeps the task open. Converge the
   original request with the built code; add unmet work as a follow-up or child,
   never rewrite the scope to match the build. For a goal, every child must be
   final and its acceptance verified.
2. Integrate the reviewed lanes in the declared order. Revalidate the review
   artifact on the merged tree at the exact head; a moved head needs a new
   artifact.
3. Reap only clean worktrees whose branch is merged. Record the commands,
   results, PR URL, and merge commit in the task Evidence, then mark it done.
4. Ship through the `shipping` skill: one ready PR, required CI green on the
   reviewed head, then merge that head. If a correction class appears twice, use
   the `correct` skill before closing.
