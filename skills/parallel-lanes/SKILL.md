---
name: parallel-lanes
description: Use when splitting work across two or three agents or sessions. Defines independent slices, ownership, worktrees, merge order, integration, and the conditions that make parallelism a net loss.
---
<!-- SPDX-License-Identifier: MIT -->

# Parallel lanes

Parallelism buys throughput only for independent work. It buys quality only
through independent review, never through more authors on the same change.

## Split test

Parallelize only when all are true:

1. The slices touch disjoint files or a fixed interface.
2. Each slice has its own acceptance criteria and can be tested alone.
3. No slice changes the shared contract after work starts.
4. Review capacity exists for each diff; otherwise you are building a queue.

Good: read-only research on different services; backend endpoint + frontend
against a written contract; two independent issuers; docs/index work beside a
code slice.

Bad: two authors in `rotate.py`/`executor.py`; concurrent edits to
`AGENTS.md`, `DECISIONS.md`, `process-lessons.md`, global config, or the state;
a refactor that moves the interface another lane is using; “one agent per
file” without a merge order.

## Plan before launching

Write an ownership map in the task or a short lane plan:

| Lane | Task | Owns (files/interfaces) | Branch/worktree | Depends on | Merge order |
|---|---|---|---|---|---|
| A | ... | ... | `feature/a` | — | 1 |
| B | ... | ... | `feature/b` | A's contract | 2 |

One lane owns the integration point. Shared files get one owner or are written
after the lanes merge. Cap at **two or three** lanes; a fourth adds coordination,
not throughput.

## Run

1. `/goal` the outcome; the plan gets one child per independent slice and
   explicit dependencies.
2. `/goal go` runs `goal-start`; it creates up to three lanes for ready
   children with disjoint `owns`. Use `/lane` only for a manual worktree or an
   existing task.
3. `/brief <task>` for each lane; fix the interface and acceptance before code.
4. Each lane works only in its worktree. It does not edit shared config, the
   state, or another lane's files.
5. At a pause, `/handoff <task>`; at review, `/review <task>`.
6. For a goal, `/close <goal>` runs the integration in the declared order,
   resolves no conflicts by guessing, reruns the full check on the merged tree,
   and reviews the merged diff. Use `/integrate` or the `integrator` agent
   directly only for an explicit branch set.
7. A green lane is not a green integration. Close each task with its own
   evidence, then close the goal.

## Stop conditions

Stop and serialize when:

- a lane needs to change an interface another lane owns;
- the same file needs edits from two lanes;
- merges conflict twice on the same area;
- review latency exceeds the time saved;
- a lane's evidence is missing or only “tests pass” without output.

Record the reason in the task log; do not silently keep both lanes running.

## Quality rule

The implementer and the reviewer are different contexts. A second author on the
same change is not a reviewer; a fresh `devils-advocate` or Jev pass is. The
merged tree gets the final review.
