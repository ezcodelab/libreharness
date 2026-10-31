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

`/goal` plans first: it writes a validated goal/child/lane JSON and stops.
Review or revise it, then `/goal go` creates and executes it; `/goal go
--unattended` also sets the per-goal continuation flag. Each child has one
scope, testable acceptance, dependencies, and a review boundary. If a child
cannot be reviewed in one sitting, split it.

Run a plan critique before execution when the goal is large or risky: Jev's
plan mode checks completeness, testability, missing dependencies, and risk.
It is advisory; fix the plan, not the score.

## Run

For each stable, unblocked child in priority order:

1. `/brief <child>`; confirm scope/acceptance.
2. Implement directly, or `/lane <child>` when two or three independent
   children can run without file/interface overlap.
3. Run the named checks; record the command and result.
4. `/review <child>`; fix send-backs.
5. `/close <child>`; the child is `done` only with evidence.
6. `goal-status <goal>`; continue or stop.

After the last child, review the goal's acceptance against the merged evidence,
run the full check on the final tree, write the goal handoff, and `/close` the
goal with that evidence.

## Stop conditions

Stop and report instead of guessing when:

- a one-way door appears (data/schema, auth boundary, public API,
  infrastructure, dependency, release);
- a child is blocked by a missing decision, credential, service, or person;
- the same child fails review twice on the same axis;
- two lanes conflict on the same file/interface;
- the next action would push, deploy, or touch production;
- the goal's acceptance is ambiguous after one clarifying question.

Leave the goal `active`, the child `blocked` or `active`, and a handoff naming
the exact next action. Do not mark a goal done to make the board green.

## Unattended mode

`goal-watch` runs whenever a goal is marked `--unattended` / `autorun: true`;
no environment flag or restart. It is bound to the creating session and bounded by
the goal's `max_continuations` (default 12). On idle it sends one continuation
prompt. It never creates tasks, marks done, pushes, or deploys. It skips if more
than one autorun goal is active. Mark the goal blocked/done to stop it.

Without the watcher, the current session still runs the loop until it stops;
the watcher only resumes after an idle boundary.

## Learning

A failed child leaves a queue log and, at close, one lesson. If the same failure
class recurs three times, the lesson becomes a project skill. Do not write a
“lesson” for every turn; only a rule that changes the next decision.
