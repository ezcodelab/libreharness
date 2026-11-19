<!-- SPDX-License-Identifier: MIT -->
# Playbook routing

## Sub-features

- `routePrompt(text)` returns `playbook`, `userNamed`, `multiStep`, and entry
  `skills`.
- A user-named playbook wins; an unknown name is ignored.
- `correct` is never selected from free text.
- `goal` is loaded only for multi-step or unattended prompts.

## How to get to it (user POV)

The intake notice states `playbook: <id>` and says whether the goal skill is
loaded. The operator sees the route before any code changes.

## Driving it with smoke.mjs

The smoke script covers the single-step route. The routing table itself is
covered by `node tests/auto-intake.test.mjs`, which drives the same
`routePrompt` export with 13 prompts.

## Observable end state

- A single-step prompt notice does not mention `goal`.
- A multi-phase prompt notice mentions `goal`.
- `routePrompt` returns `investigation` for a read-only request, even when the
  prompt starts with "Explain" and continues with "fix".

## Gotchas

- The question-only filter in `auto-intake` means a bare question does not create
  a task. `routePrompt` still classifies it, for the contract and for tests.
- Adding a playbook id means adding a table row and a
  `references/playbooks.md` section, or `harness-ratchets` fails.
