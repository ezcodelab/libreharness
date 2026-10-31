---
description: Run the EGM zero-context comprehension and readiness review
---
<!-- SPDX-License-Identifier: MIT -->
Review the task `Plan` or design document at: $ARGUMENTS

Use the `egm-design-review` skill.

1. Read the target and the files it explicitly references. Do not read the whole
   repository.
2. Run the comprehension check in a fresh subagent. If a fresh context is not
   available, stop and say so.
3. Apply the readiness checklist.
4. Report blockers, majors, and nits, then the round status.
5. Do not edit code or the target. Do not auto-apply a fix.

If the target is a task id, read the task packet first and use its `Plan`
section as the target.
