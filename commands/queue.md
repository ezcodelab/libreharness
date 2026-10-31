---
description: Inspect or maintain the durable work queue
---
<!-- SPDX-License-Identifier: MIT -->
Queue command: $ARGUMENTS

Use the work-queue skill. Run the equivalent command with separate, quoted
arguments; never interpolate raw input into a shell string.

Default with no arguments: `python3 "${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py"
ready` and then `board`, so the operator sees claimable work and the board.

Common forms:
- `list [--status <status>] [--project <name>]`
- `show <id> [--packet|--summary]`
- `ready`
- `claim <id> --owner <name> [--branch <branch>] [--base <commit>] [--worktree <path>]`
- `status <id> <status> [--note <text>] [--evidence <text>]`
- `block <id> --note <reason>` is `status <id> blocked --note ...`
- `handoff <id> --file <path>`
- `report`, `validate`, `board`

Do not hand-edit status, owner, dependencies, or evidence; evidence is recorded
only through `status ... done --evidence`. You may edit Scope, Out of scope,
Acceptance, Context, Plan, and Handoff with the edit tool; then run `validate`.
Show the command output, not a paraphrase.
