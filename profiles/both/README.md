<!-- SPDX-License-Identifier: MIT -->
# Both profile

A pilot snapshot that applies the EGM profile and the selected Superpowers
profile together. It is optional and not a default.

## What it combines

- EGM comprehension, readiness, and convergence review from `profiles/egm/`.
- The eight selected Superpowers skills from `profiles/superpowers/`.

## Use it for

A design-heavy, multi-step task where an unstated assumption and a weak
implementation plan are both plausible risks. Do not use it for a one-line fix
or a task with unambiguous acceptance.

## Conflicts

- The task `Plan` is the plan and the spec. Do not create `docs/superpowers/`
  plans or a second ledger.
- LibreHarness owns execution, lanes, worktrees, review resolution, and close.
- Do not use `executing-plans`, `subagent-driven-development`,
  `dispatching-parallel-agents`, `finishing-a-development-branch`, or
  `using-git-worktrees` from this overlay.
- The EGM comprehension check and the Superpowers evidence rules both apply,
  but the EGM review skill is the review driver. Do not run both review loops in
  parallel.

## Cost

This is the most expensive profile in the pilot: the EGM review plus the
Superpowers bootstrap and skills. The estimate is +30k to +90k tokens on a
design-heavy task. It must beat both single profiles on quality to be kept.

## Source

This is a generated pilot snapshot. `profiles/egm/` and
`profiles/superpowers/` remain the source of truth. See `NOTICE` and `LICENSE`.
