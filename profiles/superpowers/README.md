<!-- SPDX-License-Identifier: MIT -->
# Superpowers profile

An optional overlay with selected skills from
[`obra/superpowers`](https://github.com/obra/superpowers) v7.0.1, MIT. It is a
text-only profile, not the full OpenCode plugin.

## What it includes

| Skill | Why it is here |
|---|---|
| `using-superpowers` | Bootstrap that makes the agent check for a relevant skill before acting |
| `brainstorming` | Intent discovery before creative work |
| `writing-plans` | Exact files, interfaces, tests, and bite-sized steps |
| `test-driven-development` | Red-green-refactor before production code |
| `systematic-debugging` | Root cause before fixes |
| `verification-before-completion` | Fresh command output before any success claim |
| `requesting-code-review` | Fresh reviewer with a crafted diff |
| `receiving-code-review` | Verify feedback before implementing it |

`using-git-worktrees` is deliberately excluded from this first profile. The
lane and worktree boundary is owned by LibreHarness; enabling a second isolation
flow before the comparison would confound the result.

## What it excludes

- `executing-plans` and `subagent-driven-development`: they call each other's
  scripts and duplicate LibreHarness execution ownership.
- `dispatching-parallel-agents`, `finishing-a-development-branch`,
  `writing-skills`, and `diagnosing-superpowers`: deferred.
- The `brainstorming` visual-companion server, scripts, images, and telemetry
  path. The visual companion is unavailable in this profile. Do not offer it.
- The OpenCode plugin bootstrap and dynamic tool mapping. This profile uses a
  text bootstrap in `AGENTS.md`; that difference is part of the comparison and
  must be reported with the result.

## Conflicts to resolve before use

- **Plan location:** the task `Plan` is the source of truth. Do not also write
  `docs/superpowers/plans/` unless the operator asks for a separate design doc.
- **Queue versus ledger:** the LibreHarness queue owns task state and evidence.
  Do not create a second `progress.md` ledger.
- **Execution ownership:** LibreHarness goals, lanes, and tasks own execution.
  Do not invoke `executing-plans` or `subagent-driven-development`.
- **Worktree ownership:** this profile does not create worktrees. Use `/lane`
  or the operator's existing isolation.
- **Review ownership:** the profile adds reviewer skills; `devils-advocate`,
  Jev, and the task evidence gate still decide what blocks.

## Token cost

The bootstrap plus eight skills can add roughly 10k to 40k tokens on a
design-heavy task, depending on how many skills load and how often the session
compacts. Superpowers re-injects its bootstrap after compaction. Small tasks
should not use this profile.

## Attribution

Vendored skill text is MIT, copyright 2025 Jesse Vincent. The upstream license
is in `LICENSE`; the source commit and selected files are in `NOTICE`. The
profile removes executable assets and rewrites the boundary lines that named
excluded execution skills, the forbidden plan path, or removed helper files.
Those edits are listed in `NOTICE` so the comparison can account for them.
