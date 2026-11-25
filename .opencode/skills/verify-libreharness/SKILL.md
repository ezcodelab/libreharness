---
name: verify-libreharness
description: Prove LibreHarness changes on the real plugin and queue instead of mocks. Use after changing src/plugin.js, a bundled plugin, the queue CLI, or the intake notice. Launches an isolated state directory, drives one intake-to-done journey, and keeps a machine-readable report.
---
<!-- SPDX-License-Identifier: MIT -->

# Verify LibreHarness

The unit tests use mocks. This skill drives the real `src/plugin.js`, the real
bundled plugins, and the real `bin/tasks.py` against a disposable state
directory. It proves one journey: a prompt becomes a task, the task closes with
evidence, and the board and metrics exist.

## Launch

From the repository root:

```sh
node .opencode/skills/verify-libreharness/scripts/smoke.mjs
```

The script creates its own `$HARNESS_STATE` with `mkdtempSync`, so it never reads
or writes `~/.local/state/libreharness`. It needs `node` and `python3`, nothing
else.

## Doctor

Before it drives anything, the script checks:

- `src/plugin.js` imports and `setup` returns a cleanup function;
- the state directory exists with mode `0700`;
- the plugin registers the `prompt` hook and no `context` hook, because native
  OpenCode instruction discovery owns `AGENTS.md` files;
- the queue CLI answers `validate` in the temporary state.

It stops with the failed check instead of driving a half-built instance.

## Drive

One journey, in order:

1. Send a single-step prompt through the registered `prompt` hook.
2. Read the created task id from the intake notice.
3. Replace the inbox acceptance placeholder with a checked, observable criterion.
4. Write `Data shape` and `Verify: node tests/harness-ratchets.test.mjs` into the
   task Plan.
5. Run `tasks.py claim`, then `tasks.py review --run` to record the artifact.
6. Run `tasks.py status ... review` so the review gate revalidates the artifact.
7. Run `tasks.py validate` and assert exit 0.
8. Run `tasks.py status ... done --evidence` and assert the closed state.
9. Assert `work/BOARD.md` and `metrics/workflow-log.csv` exist.

## Evidence

The script writes `/tmp/opencode/verify-libreharness/latest.json` with exactly:

```json
{
  "verdict": "PASS",
  "stateDir": "/tmp/verify-libreharness-xxxx",
  "stateRemoved": true,
  "taskId": "2026...",
  "head": "<40-character git sha>",
  "verdict": "PASS",
  "checks": [{ "command": "node tests/harness-ratchets.test.mjs", "exit": 0 }],
  "verified": ["plugin.setup", "intake hook", "review artifact", "queue claim/review/done"],
  "unverified": ["OpenCode TUI transport", "GitHub Actions gate"]
}
```

`verdict` is `PASS` only when every step above ran and passed, and the review
artifact's `head` equals `git rev-parse HEAD` with current `diff_sha256` and
`contract_sha256` values. The artifact has a non-empty `checks` list containing
the ratchet command with exit 0; the report carries the same `head`, `verdict`,
and `checks`. The `unverified` list is required and names what this path cannot
reach. Never mark a remote surface verified from here.

## Cleanup

The script removes its temporary state directory after writing the report and
then re-checks that the directory is gone. The report survives cleanup. If a run
fails, cleanup still runs, and the report records the failing step.

## Helpers

`scripts/smoke.mjs` is the only helper. It is the artifact a reviewer reruns.

## Gotchas

- The intake notice is the only place the task id appears. Do not change its
  shape without updating the script.
- `tasks.py done` refuses an unchecked acceptance line, an empty evidence string,
  a `Deferred` section, or a missing/stale PASS artifact. That is the point.
- Do not point `HARNESS_STATE` at the real state directory. The script ignores
  the ambient value for that reason.
