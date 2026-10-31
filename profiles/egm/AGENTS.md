<!-- SPDX-License-Identifier: MIT -->
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
