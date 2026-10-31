<!-- SPDX-License-Identifier: MIT -->
# Profiles

A profile is an optional overlay on the base LibreHarness runtime. It is data
only: Markdown skills, commands, agents, and an optional instructions fragment.
The base runtime stays the source of truth. A profile is applied by the
benchmark adapter or by copying it into `~/.config/opencode`; it is never a
default install.

## Layout

```text
profiles/<name>/
├── README.md          when to use it, token cost, and known conflicts
├── AGENTS.md          optional instructions fragment, not a replacement
├── skills/            optional skill directories
├── commands/          optional OpenCode commands
├── agents/            optional subagent definitions
└── NOTICE             attribution and license for vendored content
```

## Rules

- Base plus profile. The adapter uploads the base runtime first, then the
  profile overlay. A profile does not edit or replace the base files.
- Record the profile name, version, and file hashes in the run manifest.
- No executable code, hooks, credentials, or network calls in a profile. A
  profile that needs code is a product change, not a profile.
- Vendor only compatible-licensed content, keep the upstream license and
  attribution in `NOTICE`, and do not copy from projects without a license.
- Vendor text only. Exclude scripts, servers, images, and any asset that makes a
  network call or ships executable code. If an upstream skill offers a visual or
  telemetry companion, the profile README must say it is unavailable.
- Keep one profile per hypothesis. A profile that mixes three ideas cannot
  tell you which one helped.
- Name the source of truth for conflicts before shipping. The known ones are
  the task `Plan` versus a separate plan file, the task queue versus a
  per-plan ledger, and LibreHarness lanes versus a separate worktree flow.
  One layer owns each; the other is a view.
- Measure before adopting. Use `bench/ablation.py` for a fast review-feature
  check or the Harbor/Terminal-Bench path for coding outcomes. A profile that
  loses on both stays optional or is deleted.

## Current profiles

| Profile | Hypothesis | Status |
|---|---|---|
| `egm` | A zero-context comprehension check, a readiness checklist, and convergence rules catch more design defects | Planned |
| `superpowers` | Selected Superpowers process skills improve planning, TDD, debugging, and verification | Planned |

The `current` arm is the base runtime with no profile. The `both` arm applies
both overlays and is expected to have the highest process cost. It must beat
both single profiles on quality and stay within the cost budget named before
the run; it is not required to be cheaper than a single profile.
