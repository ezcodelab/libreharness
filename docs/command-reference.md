<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Command reference

This page covers the slash commands in `commands/` and the queue CLI in
`bin/tasks.py`. The Jev clients have their own table at the end and a full guide
in [jev.md](jev.md).

Commands are checked against the files in this tree. If a command changes, this
page changes in the same pull request.

## Environment

Most commands resolve code and state like this:

```sh
"${HARNESS_HOME:-$HOME/.config/opencode}/bin/tasks.py"
"${HARNESS_STATE:-$HOME/.local/state/libreharness}"
```

Set both explicitly. `HARNESS_HOME` is the checkout. `HARNESS_STATE` is the
mutable queue and metrics root.

## Slash commands

Use this page after [When to use what](when-to-use.md) when you know
which command you need and want its arguments.

### `/goal`

**Use when** you have a request, task id, goal id, or reviewed plan to execute; `go` creates the goal and auto-lanes ready children.

```text
/goal <request>
/goal <task-id>
/goal <goal-id>
/goal go
/goal go --unattended
```

The single task entry.

- With a request: decide whether it is trivial, one task, or a multi-deliverable
  goal.
- With an existing task id in `inbox` or `ready`: confirm scope and acceptance,
  then execute the small-task path.
- With an existing goal id: find the next ready child; run `goal-start` once to
  lane ready children.
- With `go`: create the plan that was reviewed in `/tmp/opencode/goal-plan.json`
  after checking its SHA-256 hash, then run `goal-start` for ready children.
- With `go --unattended`: same, and set `autorun` so the goal watcher may
  continue it.

Plan mode stops before creating anything. `go` is the approval. There is no
separate apply step. `goal-start` creates up to three lanes for ready children
with disjoint `owns`, or reports serial when fewer than two are lane-able.

Plan critique is available as a standalone `bin/jev_plan.py` call. The 1.0.0
`/goal` command does not invoke it automatically. Run it after the dry run if
you want an advisory second opinion, and treat the result as evidence, not a
gate.

### `/brief`

**Use when** you are about to implement and need scope, acceptance, risks, and the first proof pinned down.

```text
/brief <task-id>
/brief <stated scope>
```

Builds a one-page brief from the task packet, project rules, and up to three
relevant lessons. Without a task id, it uses the stated scope. It does not edit
code.

### `/queue`

**Use when** you need queue state or a manual state change; most operators can start with `/goal` instead.

```text
/queue
/queue list [--status <status>] [--project <name>]
/queue show <id> [--packet|--summary]
/queue ready
/queue claim <id> --owner <name> [--branch <branch>] [--base <commit>] [--worktree <path>]
/queue status <id> <status> [--note <text>] [--evidence <text>]
/queue block <id> --note <reason>
/queue handoff <id> --file <path>
/queue report
/queue validate
/queue board
```

With no arguments, `/queue` runs `ready` and then `board`. The `block` form is
shorthand for `status <id> blocked --note <reason>`.

Do not hand-edit status, owner, dependencies, or evidence. Use the CLI.

### `/lane`

**Use when** you need a manual worktree for an existing task; normal goals auto-lane through `/goal go`.

```text
/lane <task-id>
```

Creates one isolated worktree and branch for a ready or inbox task, claims it,
and prints a worker packet. Optional flags are passed to `tasks.py lane`:

```text
--repo <path>
--name <short-name>
--base <branch-or-commit>
--setup "<command>"
--owner <lane-name>
```

The default branch is `feature/<name>`. The default worktree is
`<repo-parent>/<repo>-<name>`. This is the manual path; `/goal go` auto-lanes
ready children. If OpenCode already created a worktree, claim the task with
`--worktree`, `--branch`, and `--base` instead of creating a second one.

### `/takeover`

**Use when** you are resuming a paused or inherited task from its handoff.

```text
/takeover <task-id>
```

Reads the task packet, the Handoff section, project rules, and only the files
the handoff names. If the task is ready and unowned, it claims it. If it is
active under another owner, it stops and asks before dual-writing.

### `/review`

**Use when** a diff exists and needs a check; this is not a finish step.

```text
/review <task-id>
/review <stated task>
/review
```

Reviews the working diff. With a task id, it reads the packet and summary and
updates the task status or log at the end. Without a task id, it uses the
stated task and a session-specific temporary name. It never edits code.

The review order is Jev, then an optional `devils-advocate` pass, then a
verdict. A Jev exit 3 means "unavailable" and falls back to the independent
review path. A Jev exit 4 means the model is gone and stops the review.

### `/state-audit`

**Use when** stateful code needs its explicit and implicit state machines mapped, or a stuck, duplicate, lost, retry, or concurrency bug needs a reachable-path audit.

```text
/state-audit <repo, path, subsystem, or machine>
/state-audit
```

Writes or updates `docs/state-machines.md` in the project with states,
invariants, transition tables, ownership, recovery, and concurrency. It traces
invalid paths through retries, duplicate delivery, lock expiry, crash or
restart, partial failure, cancellation, timeouts, stale reads, and out-of-order
events. A finding is `CONFIRMED` only with `file:line` evidence and a failing
test or repro. It ranks by impact, groups by root cause, fixes the highest-impact
group with a regression test, and updates the document. If the audit is too
large, it stops after the document and grouped issues.

### `/close`

**Use when** a task or goal is ready to finish; it integrates reviewed goal lanes and reaps clean merged worktrees.

```text
/close <task-id>
```

The single finish command. For a goal with lanes it integrates the reviewed
lanes inline; for a single task with a worktree it merges the branch into an
integration branch from its base. It then runs the final review, reaps clean
merged worktrees, runs optional Jev triage, records one lesson, and transitions
to done with evidence. Missing evidence, an unfinished child, or a retained
dirty/unmerged lane keeps the task or goal open. Jev never blocks the close by
itself. A repeated correction is encoded at the highest level that works
(architecture, types, lint, test, docs) and the check is proved on the past
mistake.

### `/handoff`

**Use when** you are pausing, switching agents or sessions, or approaching the context limit.

```text
/handoff <task-id>
```

Writes or replaces the task's Handoff section. It requires a task id. The
handoff is under 40 lines and uses the fixed fields: State, Decisions, Files,
Checks, Open, Next, Context. It does not close the task.

### `/design-review`

**Use when** a UI change needs a design pass before merge; it never edits code.

```text
/design-review <screenshot path, description, or UI reference>
```

Reviews a UI against `$UI_REFERENCES_DIR` when set, otherwise the project's
`docs/ui/` directory. It loads the `ui-design` skill. If it cannot see an
image, it says so and runs the text checklist. Output is Blocking, Quick wins,
and Keep. No code edits.

### `/tune`

**Use when** a work wave is finished and you want to remove process weight; this is periodic maintenance, not a finish step.

```text
/tune
```

Runs the docs lint and reads the queue report and metrics. It mines repeated
corrections and fixes each class at the highest level that works: architecture,
types, lint, test, or docs. It proposes deletions first, then at most five
patches to `AGENTS.md`, a skill, or the named principles, each with the
evidence, the target, and a proof that the check fails on a real past mistake.
It stops for approval and promotes nothing in the turn.

## Queue CLI

For choosing between these actions, see [When to use what](when-to-use.md).
The global form is:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" [--root <state-root>] <command> ...
```

`--root` wins over `HARNESS_STATE` and is intended for tests. Put it before the
subcommand.

### `new`

```sh
tasks.py new <title> [options]
```

Options:

| Option | Meaning |
|---|---|
| `--project <name>` | Project label, default `general` |
| `--priority <0..4>` | Lower is more urgent, default 2 |
| `--depends-on <ids>` | Comma-separated task ids |
| `--scope <text>` | Scope section |
| `--acceptance <text>` | Acceptance section |
| `--tags <tags>` | Comma-separated tags |
| `--status <status>` | Initial status, default `ready` |
| `--parent <goal-id>` | Parent goal; the parent must be `kind: goal` |

Prints the new task id.

### `goal`

```sh
tasks.py goal <title> [options]
```

Creates a goal task in `active` status with owner `goal`.

Options:

| Option | Meaning |
|---|---|
| `--project <name>` | Project label |
| `--priority <0..4>` | Default 1 |
| `--scope <text>` | Goal scope |
| `--acceptance <text>` | Goal acceptance |
| `--tags <tags>` | Default `goal` |
| `--session <id>` | Session id; defaults to `OPENCODE_SESSION_ID` |
| `--autorun` | Mark the goal for the continuation watcher |
| `--unattended` | Alias for `--autorun` |
| `--max-continuations <0..100>` | Default 12 |

Prints the goal id.

### `goal-start`

```text
python3 "$HARNESS_HOME/bin/tasks.py" goal-start <goal-id> --repo <repo> \
  [--max-lanes 3] [--serial] [--json]
```

Starts ready goal children in up to three lanes with disjoint `owns`. It
preflights branch and worktree collisions before creating anything, claims each
child, and prints the lane table. With fewer than two lane-able children, or
with `--serial`, it reports serial and creates no worktrees. Use it after
`/goal go`; do not ask the operator to run `/lane` per child.

### `goal-status`

```sh
tasks.py goal-status <goal-id> [--json]
```

Shows the goal status, child counts, ready children, open children, and whether
the goal is closable. `--json` prints one object.

### `goals`

```sh
tasks.py goals [--json]
```

Lists active goals with `autorun: true`. The continuation watcher uses this.

### `plan`

```sh
tasks.py plan --file <plan.json> [--dry-run] [--json] [--expect-hash <sha256>] [--unattended]
```

Validates a goal plan and, unless `--dry-run` is set, creates the goal and its
children.

| Option | Meaning |
|---|---|
| `--file <path>` | Plan JSON |
| `--dry-run` | Validate and print, write nothing |
| `--json` | Machine-readable output, including the file hash |
| `--expect-hash <sha256>` | Refuse if the plan changed since review |
| `--unattended` | Set `autorun: true` on the created goal |

The plan schema is described in [workflow.md](workflow.md) and in
`commands/goal.md`. The validator rejects a missing goal, empty children,
duplicate keys, missing scope or acceptance, dependency cycles, overlapping
`owns` paths, and a child that is not assigned to a declared lane.

### `list`

```sh
tasks.py list [--status <status>] [--project <name>] [--json]
```

Lists tasks. `--json` returns metadata and title.

### `ready`

```sh
tasks.py ready
```

Lists tasks in `ready` status with no open dependency.

### `show`

```sh
tasks.py show <task> [--packet|--summary]
```

Shows the raw task file, the packet, or a short summary. `<task>` may be an id
or a unique prefix.

### `claim`

```sh
tasks.py claim <task> --owner <name> [--branch <branch>] [--base <commit>] [--worktree <path>] [--force]
```

Claims a `ready`, `inbox`, or `blocked` task. A goal cannot be claimed. The
command rejects open dependencies, a branch or worktree already owned by
another active or review task, and a blocked task unless `--force` is used.

### `status`

```sh
tasks.py status <task> <status> [--note <text>] [--evidence <text>]
```

Moves a task to a status. `done` requires a claimed task in `active` or
`review`, real evidence, and, for a goal, every child final. `--evidence` is
required for `done`. `--note` is used for `blocked` and is also appended to the
log.

Statuses: `inbox`, `ready`, `active`, `blocked`, `review`, `done`, `abandoned`.

### `handoff`

```sh
tasks.py handoff <task> [--file <path>] [--text <text>]
```

Replaces the Handoff section. With no `--text` and no `--file`, it reads stdin.
An empty handoff is rejected.

### `log`

```sh
tasks.py log <task> <text>
```

Appends one dated log line. It does not change status.

### `lane`

```sh
tasks.py lane <task> [--repo <path>] [--name <short>] [--base <ref>] [--path <worktree>] [--setup <command>] [--owner <name>]
```

Creates a git worktree and branch, claims the task, and prints the packet. The
default repo is the current directory. The task must be `ready` or `inbox` with
no open dependency, and the branch and worktree must not already exist.

### `remove-lane`

```sh
tasks.py remove-lane <task> [--repo <path>] [--force]
```

Removes a lane's worktree and branch. It refuses a task that is not `review`,
`done`, or `abandoned`, a dirty worktree, or a branch not merged into its base,
unless `--force` is used.

### `reap`

```sh
tasks.py reap <task-or-goal-id> [--repo <path>] [--dry-run] [--json]
```

Removes clean worktrees for a task, or for every child of a goal, only when the
task is `review`, `done`, or `abandoned` and the branch is merged into another
branch. It retains active, dirty, ignored-file, or unmerged lanes and exits 1 if
any remain. `/close` calls it after integration and review. `--dry-run` previews
the result.

### `report`

```sh
tasks.py report
```

Prints task counts, project counts, WIP against the limit of 3, the oldest
active date, and median cycle days for done tasks.

### `validate`

```sh
tasks.py validate
```

Checks ids against file names, duplicates, statuses, owners, parent links, goal
children, branch and worktree ownership, `owns` overlaps, missing dependencies,
cycles, and done tasks without evidence.

### `board`

```sh
tasks.py board
```

Regenerates `$HARNESS_STATE/work/BOARD.md`.

## Jev CLI

These are standalone commands, not slash commands. The full behavior and exit
codes are in [jev.md](jev.md).

### `jev_review.py`

```sh
python3 bin/jev_review.py --diff <file|-> [options]
```

| Option | Meaning |
|---|---|
| `--diff <file|->` | Diff file, or `-` for stdin; required unless `--check` |
| `--task <text>` | Task statement |
| `--task-file <path>` | Read the task statement from a file |
| `--model <id>` | Model id; defaults to `JEV_MODEL`, required |
| `--endpoint <url>` | Endpoint; defaults to `JEV_ENDPOINT` |
| `--models-url <url>` | Model list; defaults to `JEV_MODELS_URL` |
| `--key-file <path-or-key>` | Key file, or a literal key |
| `--timeout <seconds>` | Default 90 |
| `--max-chars <n>` | Diff and task truncation, default 30000 |
| `--json` | JSON verdict |
| `--dry-run` | Print the request payload, no call |
| `--check` | Only check model availability |
| `--allow-secret-shaped` | Send despite a secret-shaped match |
| `--mock good|bad` | Canned verdict, no network |

### `jev_plan.py`

```sh
python3 bin/jev_plan.py --goal <goal-id> [options]
```

| Option | Meaning |
|---|---|
| `--goal <id>` | Goal task id; required |
| `--root <path>` | State root; defaults to `HARNESS_STATE` or the checkout |
| `--model <id>` | Defaults to `JEV_MODEL`, required |
| `--endpoint <url>` | Defaults to `JEV_ENDPOINT` |
| `--key-file <path-or-key>` | Key file, or a literal key |
| `--timeout <seconds>` | Default 90 |
| `--json` | JSON result |
| `--dry-run` | Print the request payload, no call |
| `--mock good|bad` | Canned result, no network |

### `jev_triage.py`

```sh
python3 bin/jev_triage.py --state <file> [options]
```

| Option | Meaning |
|---|---|
| `--state <file>` | File with the compact close state; required |
| `--model <id>` | Defaults to `JEV_MODEL`, required |
| `--endpoint <url>` | Defaults to `JEV_ENDPOINT` |
| `--key-file <path-or-key>` | Key file, or a literal key |
| `--timeout <seconds>` | Default 90 |
| `--json` | JSON result |

Triage has no `--mock` or `--dry-run` in 1.0.0.

## Exit codes

Queue commands return 0 on success and a non-zero code on an error. They print
the error to stderr.

Jev clients use:

| Exit | Meaning |
|---|---|
| 0 | Pass, or advisory result produced |
| 2 | Send back or no durable lesson |
| 3 | Configuration, API, missing key, or secret-shaped input |
| 4 | The requested model is gone |

## Next

- [Skills](skills.md)
- [Plugins](plugins.md)
- [Jev](jev.md)
