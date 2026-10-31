<!-- SPDX-License-Identifier: MIT -->
# Both profile rules

The base LibreHarness rules, queue, task `Plan`, lanes, review protocol, and
evidence gate remain the source of truth. This overlay combines the EGM design
review with the selected Superpowers process skills.

Use EGM for a nontrivial design or multi-file change. Use Superpowers for
planning, TDD, debugging, review, and verification. Do not use the excluded
execution skills or create a second plan/ledger/worktree.

## EGM rules

# EGM profile rules

Use the `egm-design-review` skill for a nontrivial design or multi-file change
before implementation.

The base LibreHarness rules, queue, task `Plan`, review protocol, and evidence
gate still apply. This profile adds a review step; it does not replace them.

Rules:

1. The task `Plan` is the spec. If the task is a one-way door, use the existing
   decision memo instead of creating a second design document.
2. Run the comprehension check in a fresh subagent. If the harness cannot create
   a fresh context, say so and stop; a same-context review is not the check.
3. Treat an unparaphrasable section as a blocker. A missing definition or an
   unstated prerequisite is a gap, not a style issue.
4. Keep only blockers and majors in the adoption decision. Nits are recorded and
   do not block.
5. A settled finding stays settled. A fixed finding re-opens if it returns at
   the same scope. A clean round has no unsettled blocker or major. Stop after
   two consecutive clean rounds or five rounds, whichever comes first.
6. The operator or `devils-advocate` resolves findings. Do not auto-apply a fix
   from the review report.
7. Do not use this profile for a one-line fix or a task with unambiguous
   acceptance.

## Superpowers rules

# Superpowers profile rules

Before acting on a coding request, check whether one of the installed
Superpowers skills applies and load it. Process skills come first:

- a new feature or design discussion: `brainstorming`;
- a multi-step implementation: `writing-plans`;
- production code: `test-driven-development`;
- a bug or failing test: `systematic-debugging`;
- a completion claim: `verification-before-completion`;
- a review request or review feedback: `requesting-code-review` or
  `receiving-code-review`.

The base LibreHarness rules, queue, task `Plan`, lanes, review protocol, and
evidence gate remain the source of truth. A skill that conflicts with them is
not applied.

Specific boundaries:

1. Do not use `executing-plans`, `subagent-driven-development`,
   `dispatching-parallel-agents`, `finishing-a-development-branch`, or
   `using-git-worktrees` from this profile. They are not installed, and
   LibreHarness owns execution and integration.
2. Do not create `docs/superpowers/plans/` or a separate `progress.md` ledger.
   Use the task `Plan` and the queue.
3. The `brainstorming` visual companion is unavailable. Do not offer it, start
   a server, or fetch its assets. Use the text questions only.
4. Do not let a skill claim completion. Run the task acceptance check and show
   the output before saying the work is done.
5. Use this profile for design-heavy or multi-step work. For a one-line fix or a
   task with unambiguous acceptance, use the base LibreHarness workflow.
