---
name: verification
description: Generate a project-local verification recipe when a change needs proof against the real app and the project has no scripted way to drive it. Use for "verify this", "prove it works", "drive the app", or a missing test path.
---
<!-- SPDX-License-Identifier: MIT -->

# Verification skill generator

Use when a change needs proof against the real app and the project has no
scripted way to launch, drive, and observe it. The deliverable is a
project-local skill that the next agent can run cold.

Do not use this for a change already covered by a direct test, type check, or
lint. If the app cannot start, report the blocker before generating anything.

## 1. Interview the repo, not the user

Answer these from the code. Ask only what the code cannot show.

- **Surface:** what does a user touch? Web UI, CLI or TUI, API, desktop app,
  mobile app, or library? Pick the primary surface; note the rest.
- **Run:** exact local launch command, ports, env vars, seed data, auth, and
  the readiness signal. Prefer the repo's own documented command.
- **Drive:** how can an agent interact programmatically? Existing Playwright,
  Cypress, expect, PTY, or curl harnesses first; otherwise browser/CDP, tmux or
  a PTY, or plain HTTP.
- **Observe:** what proves the result? Screenshots, terminal transcripts,
  response bodies, logs, exit codes, database rows, or files written.
- **Isolate:** can two instances run side by side on different ports and data
  directories? If not, the generated skill must refuse to double-drive.

If the checkout does not build or start as-is, fix that first or report the
exact blocker. A skill written against a broken base teaches wrong steps.

## 2. Generate the project skill

Write `.opencode/skills/verify-<app>/SKILL.md` with frontmatter:

```yaml
---
name: verify-<app>
description: Drive <app> through its real <surface> and capture proof. Use after changes to <feature area>.
---
```

Include these sections, grounded in what the interview found. No placeholders.

- **Launch:** the exact command, readiness check, and teardown. Launch from an
  empty data directory, including migrations and seed data.
- **Doctor:** one read-only check that answers "is this instance worth
  driving?" Check the process, version, port ownership, and auth.
- **Drive:** real selectors, commands, and routes from this repo. Prefer stable
  handles such as ARIA labels, data attributes, prompt strings, and route paths
  over coordinates or tab order.
- **Evidence:** the real user path and the resulting state, not a test-only
  setter or a final screenshot alone. Verify side effects such as files, rows,
  messages, or git refs. Mocks are allowed only at a production boundary.
- **Cleanup:** kill only what the run started. Never kill by process name.
  Cleanup removes instances and scratch state, never the evidence.
- **Helpers:** every script is executable and its invocation appears in the
  skill. A helper the reader has to reverse-engineer is not a helper.

For a short-lived CLI or TUI, "launch" means build or install once, then start
each drive in its own isolated PTY or tmux session.

## 3. Seed the feature map

Create `.opencode/skills/verify-<app>/features/README.md` and one file for the
top three to five user-facing features. Each file answers, from the user's
point of view:

- **Sub-features:** what the feature includes.
- **How to get to it (user POV):** the route, command, or menu path.
- **Driving it with <harness>:** the concrete steps and selectors.
- **Gotchas:** preconditions, seed data, known traps.

If the seed data lacks a precondition, the journey fails with that reason. Do
not weaken the journey to make it pass. The map is the maintained source of
truth, not a demo of one convenient path.

## 4. Prove the generated skill once

Run the generated skill end to end: launch, doctor, drive one mapped feature,
capture evidence, and clean up. After cleanup, confirm the evidence still
exists at the named path. Fix what fails, and run cleanup after every failed
attempt so processes and ports do not leak.

If the proof ran in a stand-in such as a container or a local stack, list every
setup step the real target will still need. Those steps stay unverified until a
real run covers them.

## 5. Hand off the maintenance loop

Report the generated paths, the exact proof command and result, and what
remains unverified. Re-run the skill when the app's launch path, routes, or
user-facing features change. A stale feature map is a false green.

## Stop conditions

Stop and report instead of generating a green check when:

- the app does not build or start from a clean checkout;
- there is no stable way to drive or observe the real surface;
- the only available instance is shared and cannot be isolated;
- the check would mutate production, shared data, or an external account;
- the evidence cannot survive cleanup.

## Evidence standard

A proof is a real user path plus the resulting observable state, with the
command and output kept for a reviewer. "It compiles", a passing unit test, or
a screenshot of the final screen alone is not enough when the change is about
user-visible behavior.

Name the principle that shaped the proof. "Prove it works" and "Sequence
verifiable units" are the usual ones.
