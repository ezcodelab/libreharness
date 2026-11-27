<!-- SPDX-License-Identifier: MIT -->
# Brief

Build a one-page brief for the task before editing.

1. Read the task packet with `tasks show <id> --packet`. If there is no task,
   state that and use the stated scope.
2. Read the project `AGENTS.md`, `CONTRIBUTING.md`, and only the files or tests
   the task names. Do not read the whole repository.
3. Read the decisions or lessons in `AGENTS.md`, `DECISIONS.md`, or the project
   docs. Keep only lessons that change the next action.
4. Name the injected skills that apply.

Output in this order:

- **Task** and one-sentence scope
- **Playbook**: the `engineering-loop` row that matches, or the fallback and why
- **Out of scope**
- **Data shape**: types, state machine, boundary parser, and the owner of each
  piece of state
- **Acceptance** as observable checks
- **Reach**: callers, importers, tests, fixtures, config, exports, and
  wire-format consumers the change must touch or preserve
- **Invariants** and trust boundaries
- **Risks and unknowns**
- **Definition of done**
- **Past lessons**: zero to three, with why each applies
- **First action** and the exact check that proves it

Write one `Data shape:` line and one `Verify:` line into the task `## Plan`
before claim. `Data shape` is a non-empty JSON object or array, or
`path <repo-relative-file>#<symbol>`, or `none - <reason>` only for a docs or
chore task. `Verify` is one command from the review allowlist. A product task
that cannot name its real check stays unverified; do not point Verify at a
harness check. Stop after the brief; do not edit code in the same step.
