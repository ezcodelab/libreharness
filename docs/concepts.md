<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Concepts

This page defines the terms used by the queue, commands, skills, and review
workflow. The CLI is the source of truth; if this page and the CLI disagree,
the CLI wins and the page is wrong.

## Two roots

| Root | Meaning | Examples |
|---|---|---|
| `HARNESS_HOME` | Code and configuration | `bin/tasks.py`, `commands/`, `skills/`, `plugins/`, `opencode.json` |
| `HARNESS_STATE` | Mutable local data | tasks, board, lock, metrics, optional Jev key file |

With the V2 plugin, the plugin sets `HARNESS_HOME` to its own package root.
OpenCode configuration stays in `~/.config/opencode`, and state defaults to
`~/.local/state/libreharness` as a real mode-700 directory.

The rule is simple: code is read-mostly and can be replaced by a checkout;
state is the user's work and must survive an upgrade. No runtime component
should write into `HARNESS_HOME`.

`HARNESS_STATE` currently contains:

```text
$HARNESS_STATE/
├── work/
│   ├── tasks/
│   │   └── <yyyy-mm-dd>-<slug>.md
│   ├── BOARD.md
│   └── .lock
└── metrics/
    └── workflow-log.csv
```

`work/.lock` is created on first write. `work/BOARD.md` is generated; edit task
files, not the board. The metrics file gets one row when a task first reaches
`done`.

## Task

A task is one Markdown file. It should fit one agent session and one reviewable
diff.

Frontmatter holds the machine-readable fields:

| Field | Meaning |
|---|---|
| `id` | Date-based id; must match the file name |
| `title` | Human title |
| `project` | Project label, default `general` |
| `kind` | `task` or `goal` |
| `status` | One of the status values below |
| `priority` | 0 to 4; lower number is more urgent |
| `owner` | Session, person, or lane that claimed it |
| `parent` | Goal id for a child task |
| `session` | Optional session id, used by the continuation watcher |
| `lane` | Optional lane name |
| `owns` | Comma-separated repo-relative paths this task may change |
| `branch`, `worktree`, `base` | Lane isolation fields |
| `depends_on` | Comma-separated task ids that must finish first |
| `reviewer` | Optional reviewer label |
| `autorun`, `max_continuations` | Per-goal continuation policy |
| `blocked_reason` | Why a task is blocked |
| `created`, `updated` | Dates |
| `tags` | Comma-separated labels |

The body has these sections: Scope, Out of scope, Acceptance, Context, Plan,
Evidence, Handoff, and Log. Scope and Acceptance are required in practice even
if the file starts with a placeholder.

## Status values

| Status | Meaning |
|---|---|
| `inbox` | Captured, not yet shaped. Auto-intake creates these. |
| `ready` | Has scope and acceptance, no open dependency, claimable |
| `active` | Claimed by one owner and being worked |
| `blocked` | Waiting on a decision, dependency, or external fact |
| `review` | Work is ready for review or integration |
| `done` | Final, with evidence |
| `abandoned` | Final, deliberately not done |

`done` and `abandoned` are final. A task can move from `active` or `review` to
`done`; it cannot jump from `inbox` or `ready` to `done`. That rule prevents a
task from being closed without ever being claimed and checked.

## Acceptance and evidence

Acceptance is an observable check, not a wish. Good acceptance items name a
command, a test, a measured value, or a concrete behavior:

```text
- [ ] `python3 -m unittest tests.test_queue` passes
- [ ] `GET /health` returns 200 after a restart
- [ ] the generated board contains the task id
```

Evidence is the result that proves an acceptance item. The queue rejects these
placeholder values: `none`, `n/a`, `na`, `tbd`, `ok`, `pass`, `done`, and
`tests pass`. It also rejects empty evidence.

Accepted evidence looks like:

```text
python3 -m unittest discover -s tests -p 'test_*.py': 18 tests, OK
```

```text
curl -fsS localhost:8080/health: HTTP 200
```

```text
[T] Harbor is not installed; adapter tests are skipped in this environment
```

The last form is a tracked deferral, not a pass. Say what is unproven and what
would change it.

## Goal

A goal is an umbrella task with `kind: goal`. It has child tasks and its own
scope and acceptance. A goal is done only when every child is final and its
acceptance is checked.

A goal is not permission to skip review. It is a way to keep a multi-deliverable
outcome visible across sessions. The `/goal` command plans first for a
multi-deliverable request, then `/goal go` creates the validated plan.

The plan validator checks:

- every child has scope and acceptance;
- dependencies exist and form no cycle;
- `owns` paths are repo-relative and do not overlap another child or a live
  task;
- lanes are declared and each child is assigned at most once;
- a goal has at least one child.

## Lane

A lane is an isolated branch and worktree for one task. It exists so two
independent slices can proceed without editing the same files.

A lane record includes the task, branch, base commit or branch, worktree path,
owner, and the paths the lane owns. `tasks.py lane` creates the worktree and
branch, claims the task, and prints the task packet.

Parallelism is capped at two or three lanes. Shared files get one owner. A lane
does not push. One integrator merges in the declared order and runs the full
check on the merged tree. A green lane is not a green integration.

## Handoff

A handoff is a bounded state transfer for the next session. It goes in the
task's Handoff section and covers:

- state: done, in progress, or blocked;
- decisions and why;
- files changed, especially the one or two that matter;
- checks run, result, and timestamp, with "not run" allowed;
- open questions and risks;
- one bounded next action;
- links to the task, index, lesson, and review.

A handoff is not a lesson and not a transcript. Keep it under 40 lines. Do not
put a secret, token, full log, or personal data in it.

## Review

Review is proportional to risk. The harness has three inputs:

1. **Acceptance and evidence.** Does the diff do what the task says, and is
   there a check that proves it?
2. **Jev.** An advisory typed-question review. It returns scores and a verdict,
   or a configuration error. It does not block by itself.
3. **Independent challenge.** The `devils-advocate` agent runs only when Jev
   sends back, the change touches a risky boundary, the operator asks for a
   strict review, or Jev is unavailable.

A finding is labeled `CONFIRMED`, `REFUTED`, or `UNVERIFIED`. Only a confirmed
high-severity finding blocks. `UNVERIFIED` is a warning that needs more
evidence, not a defect.

## Close

Close is the final step. It:

1. checks every acceptance item and its evidence;
2. runs the final review if there is a diff;
3. runs Jev close triage when Jev is configured;
4. appends one dated lesson entry to the project's process ledger, or says
   "Surprise: none";
5. records the evidence on the task with `status ... done --evidence`;
6. reports what passed, what remains unproven, and the next action.

Jev triage is advisory. It never blocks the close by itself.

## Priority and WIP

Priority is 0 to 4. Lower is more urgent. The report warns when more than three
tasks are active. The limit is a signal, not an enforced block, because a
person may have a legitimate reason to exceed it.

## Configuration versus state

| Thing | Belongs in | Why |
|---|---|---|
| Command definitions, skills, agents, plugins | `HARNESS_HOME` | Reviewed, versioned, replaceable |
| Provider and model choice | OpenCode config | User and provider specific |
| Jev endpoint and model | Environment | User and provider specific |
| Tasks, board, metrics, lock | `HARNESS_STATE` | Mutable work data |
| Jev key | Environment or a mode 600 key file | Secret, never committed |
| Project rules | The project repository | Travels with the code |
| Portable lessons | The state directory or project ledger | Local operational knowledge |

Do not put mutable state in the code tree. Do not put a secret in the state
tree unless it is a mode 600 key file that the client explicitly reads.

## Next

- [Workflow](workflow.md)
- [Command reference](command-reference.md)
- [Security and privacy](security-privacy.md)
