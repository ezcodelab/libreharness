<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Quickstart

This walkthrough creates, claims, reviews, and closes one task in a temporary
state root. It takes a few minutes and does not need a Jev key.

You need a checkout and Python 3.10 or newer. The commands work from the
checkout root.

## 1. Set a temporary state root

```sh
export HARNESS_HOME="$PWD"
export HARNESS_STATE="$(mktemp -d)"
```

`HARNESS_HOME` is the code. `HARNESS_STATE` is the data. Using a temporary state
root means nothing here can disturb real work.

## 2. Create a task

```sh
ID=$(python3 "$HARNESS_HOME/bin/tasks.py" new "Try the harness" \
  --project demo \
  --scope "Create and close one task." \
  --acceptance "- board lists the task")
printf '%s\n' "$ID"
```

Expected output is a date-based id:

```text
20261030-try-the-harness
```

The exact date changes. The id is the file name under
`$HARNESS_STATE/work/tasks/`.

The command also writes `$HARNESS_STATE/work/BOARD.md`. The task starts in
`ready`.

## 3. Claim it

```sh
python3 "$HARNESS_HOME/bin/tasks.py" claim "$ID" --owner quickstart
```

Expected output:

```text
claimed: 20261030-try-the-harness by quickstart
```

The status is now `active` and the owner is recorded. Claiming a goal is
rejected; claim a child task instead.

## 4. Move it to review

```sh
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" review \
  --note "quickstart walkthrough"
```

Expected output:

```text
20261030-try-the-harness: review
```

In a real task, this is where you run the documented checks and `/review`.

## 5. Close it with evidence

```sh
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" done \
  --evidence "python3 bin/tasks.py board: task listed"
```

Expected output:

```text
20261030-try-the-harness: done
```

The evidence gate rejects a placeholder. These all fail:

```text
none
ok
pass
done
tests pass
```

Use a command and result, a measured check, or an explicit `[T]` with a plan.
The evidence is appended to the task's Evidence section and one row is written
to `$HARNESS_STATE/metrics/workflow-log.csv`.

## 6. Inspect the board

```sh
python3 "$HARNESS_HOME/bin/tasks.py" board
cat "$HARNESS_STATE/work/BOARD.md"
```

The board has a Done section with one row:

```text
| 2 | `20261030-try-the-harness` Try the harness | demo | quickstart |  | 2026-10-30 |
```

The exact date and column spacing may differ.

## 7. Inspect the task file

```sh
cat "$HARNESS_STATE/work/tasks/$ID.md"
```

The file starts with YAML-like frontmatter and has these sections: Scope, Out
of scope, Acceptance, Context, Plan, Evidence, Handoff, and Log. You may edit
Scope, Out of scope, Acceptance, Context, Plan, and Handoff. Do not hand-edit
status, owner, dependencies, or evidence. Use the CLI so the board and metrics
stay consistent.

## 8. Clean up

```sh
rm -rf "$HARNESS_STATE"
```

`HARNESS_STATE` was a temporary directory. Removing it removes the demo task,
board, and metrics.

## What just happened

```text
new -> ready -> claim -> active -> status review -> review -> done with evidence
```

The queue is a set of Markdown files plus a lock. There is no database and no
server. The board is generated from the files. The lock serializes writers so
two tasks cannot claim the same branch or worktree, and writes are atomic so a
crash does not leave a half-written task.

## Try Jev without a key

Jev is optional. To see its request shape and verdict without a network call:

```sh
printf 'diff --git a/demo.txt b/demo.txt\n+hello\n' > "$HARNESS_STATE/quickstart.diff"
JEV_MODEL=example-model python3 "$HARNESS_HOME/bin/jev_review.py" \
  --mock good \
  --diff "$HARNESS_STATE/quickstart.diff" \
  --task "Quickstart demo"
```

`--mock good` returns a canned pass. `--mock bad` returns a canned send-back.
The model name is still required because the client validates it before the
mock branch. The mock does not call the endpoint and does not need a key.

For a live call, see [jev.md](jev.md).

## Next

- Read [workflow.md](workflow.md) for the full loop.
- Read [concepts.md](concepts.md) for the terms.
- Read [command-reference.md](command-reference.md) for every command and
  argument.
