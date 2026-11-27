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

## Entry

This skill is the manual goal entry and the execution procedure. When the
request names an existing task or goal id, read its packet. For a goal, call
`tasks` with `goal-status`, then `goal-start`. Execute each ready child with the
`work-queue` brief, implement, review, and close. Use `tasks lane` only when the
operator explicitly wants a manual worktree.

When the request is new, brief it with the `work-queue` brief reference, plan it
here, show the plan, and stop for approval before creating it.

## Create

The goal flow plans first: it writes a validated
goal/child/lane JSON and stops. Review or revise it, then create and execute it;
the manual form is `/goal go`, and `--unattended` sets the per-goal continuation
flag. Each child has one scope, testable acceptance, dependencies, and a review
boundary. If a child cannot be reviewed in one sitting, split it. For a
multi-child goal, shape each one with `references/spec-shape.md`. The reviewed
lane map is used by `goal-start`; the operator does not create lanes by hand.

## Run

After creating or resuming a goal, run `tasks goal-start <goal> --repo
<repo>` once. It creates lanes for ready children with disjoint `owns`; use
`--max-lanes` only as an explicit operator budget. If it reports serial, work in
the current tree. Use `tasks lane` only for a worktree you deliberately want
outside the goal.

For each stable, unblocked child in priority order:

1. Brief the child with the `work-queue` brief reference; confirm
   scope/acceptance.
2. Implement in the assigned lane, or directly when `goal-start` reported
   serial.
3. Run the named checks; record the command and result.
4. Run the review step (the `/review` command is its manual form); fix
   send-backs.
5. Close the child (the `/close` command is its manual form); the child is
   `done` only with evidence. Ship each independently shippable child as its
   own small PR off trunk. Stack only a child that needs the code below it, and
   land the stack bottom-up. Do not combine independent children into one large
   integration PR.
6. `goal-status <goal>`; continue or stop.

When every child is final, run the close step. It verifies that child PRs
merged, not that their lanes are combined into one branch.

After the last child, review the goal's acceptance against the merged evidence
on current trunk, run the full check, write the goal handoff, and close the goal
with that evidence. Converge first: compare every requirement and acceptance
item with the code on trunk. Append unbuilt work as a child; never rewrite the
scope to match what was built. Integrate a combined branch only when the goal has a
cross-lane acceptance that cannot be proved on trunk; that integration is
itself split by review boundary.

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
creating session on idle while the goal makes progress; an explicit
`max_continuations` caps it. It skips if more than one autorun goal matches. For
any active goal whose children are all final, it sends one closable reminder per
goal per session, including a goal from another session. The operator can reply
"close now" to run `/close` or "later" to keep it open. The watcher never
creates tasks, closes a goal, marks anything done, pushes, or deploys.

Without the watcher, the current session still runs the loop until it stops;
the watcher only resumes after an idle boundary.

## Learning

A failed child leaves a queue log and, at close, one lesson. When the same
failure class recurs, the lesson becomes a project skill. Do not write a
"lesson" for every turn; only a rule that changes the next decision.
