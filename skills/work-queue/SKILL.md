---
name: work-queue
description: Use when work is nontrivial, spans more than one session, or will run in parallel. Creates and maintains durable tasks in the state work queue with scope, acceptance criteria, ownership, dependencies, evidence, and handoff.
---
<!-- SPDX-License-Identifier: MIT -->

# Work queue

A task is the unit of context: one task should fit one agent session and one
reviewable diff. The queue is durable; chat history is not.

## When to use it

Create a task before editing when any of these is true:

- the change is nontrivial (external API, secrets, schema, security, multi-file);
- the work will outlive this session or move between agents;
- two or more lanes will run in parallel;
- a dependency, review, or operator decision must be visible later.

Trivial fixes do not need a task. Do not create a task for a typo.

## Tools

Call the `tasks` tool with `args`; it runs the queue in the session directory.

- `new "Title" --project demo --priority 1 --scope "One sentence." --acceptance "- [ ] testable claim"`
- `ready`
- `show <id> --packet`
- `claim <id> --owner lane-a --branch <branch> --base <base> --worktree <path>`
- `status <id> review --note "..."`
- `status <id> done --evidence "make check: 42 passed"`
- `handoff <id> --file <os-temp>/handoff.md`
- `validate`
- `report`

`/goal` is the task-entry command. Use the `tasks` tool directly for queue
inspection, lanes, resume, and handoff; do not add wrapper commands.

## Brief

Use `references/brief.md` before claim. Write one `Data shape:` line and one
`Verify:` line into the task Plan, then stop before editing.

## Resume

Read the packet and handoff, run the last check if safe, and claim only when the
task is ready and unowned. Stop on a dual owner.

## Handoff

Use `references/handoff.md`. Write the file first, save it with `tasks handoff
<id> --file <path>`, then run `tasks handoff <id> --check`.

## Goals

A multi-step outcome uses `/goal` and the `goal` skill: a `kind: goal` umbrella
with child tasks (`--parent <goal>`). A goal is never claimed or laned; its
children are. A goal is done only when every child is final and its own
acceptance is verified.

## Lifecycle

`inbox → ready → active → review → done`, with `blocked` and `abandoned` as
exits. `review` means the review artifact is PASS and the task is awaiting
integration or close; the status gate revalidates the artifact. A task is
claimable only when `ready` and every dependency is `done` or `abandoned`. One
owner and one branch/worktree per active task.

The task file holds:

- **Scope** and **Out of scope**;
- **Acceptance**: observable checks, not a wish;
- **Context**: links to the project index, decisions, and lessons;
- **Plan**: the chosen path, one `Data shape` line, one `Verify` command, and
  interfaces;
- **Evidence**: checks actually run, with results, or `[T]` with a plan;
- **Handoff**: the state a fresh agent needs;
- **Log**: append-only state changes.

`work/BOARD.md` is generated; never edit it. The task files are the source of
truth.

## Rules

- Do not claim a task with open dependencies unless the operator explicitly
  accepts the risk; record why in the log.
- Do not mark `done` without evidence. `none` is not evidence.
- Do not put secrets, tokens, or production values in a task file.
- Keep one task per session and one reviewable diff per task. Split a task that
  cannot be reviewed in one sitting.
- Update the task before switching context; a fresh agent reads the task and
  handoff, not the old transcript.
- When the task changes scope, edit Scope/Acceptance first and log why. A
  silent scope change is the defect.
