<!-- SPDX-License-Identifier: MIT -->
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
