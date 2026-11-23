---
name: goal
description: Use when the operator sets a multi-step outcome and wants the agent to work through it, optionally unattended. Creates a goal umbrella and child tasks, runs the queue, stops on one-way doors or blockers, and closes only when every child has evidence.
---
<!-- SPDX-License-Identifier: MIT -->

# Goal loop

A goal is a durable umbrella over child tasks. It is not permission to skip
review or to mutate production.

## Shape

```text
goal <id>                  kind: goal, active, owner: goal, autorun: true|false
  child <id>               session-sized task, parent: <goal>
  child <id>               dependency, acceptance, evidence
```

A goal is done only when every child is `done` or `abandoned` and the goal's
own acceptance is checked. A goal is never claimed or laned; its children are.

## Create

The goal flow plans first (manual form `/goal`): it writes a validated
goal/child/lane JSON and stops. Review or revise it, then create and execute it;
the manual form is `/goal go`, and `--unattended` sets the per-goal continuation
flag. Each child has one scope, testable acceptance, dependencies, and a review
boundary. If a child cannot be reviewed in one sitting, split it. The reviewed
lane map is used by `goal-start`; the operator does not create lanes by hand.

## Run

After creating or resuming a goal, run `tasks.py goal-start <goal> --repo
<repo>` once. It creates up to three lanes for ready children with disjoint
`owns`. If it reports serial, work in the current tree. The manual `/lane`
command is only for a worktree you deliberately want outside the goal.

For each stable, unblocked child in priority order:

1. Brief the child (the `/brief` command is its manual form); confirm
   scope/acceptance.
2. Implement in the assigned lane, or directly when `goal-start` reported
   serial.
3. Run the named checks; record the command and result.
4. Run the review step (the `/review` command is its manual form); fix
   send-backs.
5. Close the child (the `/close` command is its manual form); the child is
   `done` only with evidence.
6. `goal-status <goal>`; continue or stop.

When every child is final, run the close step; it integrates reviewed lanes as
part of the finish path.

After the last child, review the goal's acceptance against the merged evidence,
run the full check on the final tree, write the goal handoff, and close the goal
with that evidence.

## Stop conditions

Stop and report instead of guessing when:

- a one-way door appears (data/schema, auth boundary, public API,
  infrastructure, dependency, release);
- a child is blocked by a missing decision, credential, service, or person;
- the same child fails review twice on the same axis;
- two lanes conflict on the same file/interface;
- the next action would deploy, touch production, or mutate shared
  infrastructure; a verified PR push/merge is part of the normal path;
- the goal's acceptance is ambiguous after one clarifying question.

Leave the goal `active`, the child `blocked` or `active`, and a handoff naming
the exact next action. Do not mark a goal done to make the board green.

## Unattended mode

`goal-watch` has two jobs. For an `autorun: true` goal, it continues the
creating session on idle, bounded by `max_continuations` (default 12), and skips
if more than one autorun goal matches. For any active goal whose children are
all final, it sends one closable reminder per goal per session, including a goal
from another session. The operator can reply "close now" to run `/close` or
"later" to keep it open. The watcher never creates tasks, closes a goal, marks
anything done, pushes, or deploys.

Without the watcher, the current session still runs the loop until it stops;
the watcher only resumes after an idle boundary.

## Learning

A failed child leaves a queue log and, at close, one lesson. If the same failure
class recurs three times, the lesson becomes a project skill. Do not write a
"lesson" for every turn; only a rule that changes the next decision.
