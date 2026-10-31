---
description: Take over a queued or paused task from its packet and handoff
---
<!-- SPDX-License-Identifier: MIT -->
Takeover: $ARGUMENTS

Use the work-queue skill and the handoff section in `engineering-loop`. Do not
edit code until the state is clear.

1. Require a task id. `tasks.py show <id> --packet`.
2. If the task is `ready` and unowned, claim it for this session's lane. If it
   is `active` under another owner, stop and ask before dual-writing.
3. Read the task's Handoff, the project `AGENTS.md`, the relevant
   `DECISIONS.md` standing rules, and `docs/INDEX.md`. Read only the files the
   handoff names plus what the next action needs. Load at most two matching
   lessons and one matching skill.
4. Run the check the handoff says was last run, if it is safe and local. Treat
   "done" as a claim until the check reproduces.
5. Output: **State**, **What is proven**, **What is open**, **Next action**
   (one bounded action), **Context loaded / skipped**. Then stop for the
   operator unless the next action is a trivial, reversible read-only check.
