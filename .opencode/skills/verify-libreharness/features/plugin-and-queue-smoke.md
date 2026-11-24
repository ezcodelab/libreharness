<!-- SPDX-License-Identifier: MIT -->
# Plugin and queue smoke

## Sub-features

- `plugin.setup` registers commands, agents, skills, and the three bundled plugins.
- `auto-intake` turns one prompt into an inbox task with an intake notice.
- `tasks.py` enforces claim, review, validate, and done with a PASS artifact.
- The board, workflow log, and usage mapping appear in the state directory.

## How to get to it (user POV)

Describe a non-trivial change in an OpenCode session. The harness creates a task,
states the playbook, and asks for acceptance plus the Data shape and Verify lines.
The operator then reads the task, the board, and the evidence.

## Driving it with smoke.mjs

```sh
node .opencode/skills/verify-libreharness/scripts/smoke.mjs
```

The script covers the whole list above in one run and writes
`/tmp/opencode/verify-libreharness/latest.json`.

## Observable end state

- `verdict` is `PASS`.
- `taskId` names a task whose status is `done`.
- `stateRemoved` is `true` and the directory is gone.
- `verified` names the steps that ran; `unverified` names what the path cannot
  reach.

## Gotchas

- The script must own `$HARNESS_STATE`. An ambient value is ignored.
- `done` fails on an unchecked acceptance line, empty evidence, or a `Deferred`
  section. Fix the task, not the check.
- This path does not exercise the OpenCode TUI or the GitHub Actions gate. Those
  stay in `unverified` until a run covers them.
