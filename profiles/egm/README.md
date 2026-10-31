<!-- SPDX-License-Identifier: MIT -->
# EGM profile

An optional overlay that adds a lightweight version of three ideas from
Google's Elephant-Goldfish Model:

1. a zero-context comprehension check;
2. an implementation-readiness checklist;
3. settled/fixed/clean-round review convergence.

It does not add the full EGM plugin, its brainstorm/draft pipeline, or its
multi-persona swarm. The base LibreHarness queue, goal, lane, review, and close
contracts stay in force.

## When to use it

- A multi-file feature or a design decision that is expensive to reverse.
- A spec that will be handed to another session or engineer.
- A task where the main risk is an unstated assumption, not a typo.

Do not use it for a one-line fix, a mechanical rename, or a task whose
acceptance is already unambiguous. Those tasks pay the context cost without a
corresponding risk.

## What it adds

- `skills/egm-design-review/SKILL.md`: the comprehension check, readiness
  checklist, severity rules, and convergence rules.
- `commands/comprehend.md`: a short command that invokes the skill.
- `AGENTS.md`: an instruction fragment appended to the base rules.

## Conflicts to resolve before use

- The base task `Plan` remains the spec. Do not create a second design document
  unless the task is a one-way door that already needs a decision memo.
- The base review protocol remains the review record. The EGM skill produces
  findings; `devils-advocate` or the operator resolves them. EGM does not
  replace the evidence gate.
- The base queue remains the source of truth for completion. A review report is
  evidence, not a task status.

## Token cost

One comprehension call reads the spec, the files it references, and the skill
instructions. Expect roughly 15k to 30k additional input tokens per review on a
small-to-medium spec. It is cheap on a large task and expensive on a small one;
use the task-size boundary above.

## Attribution

The method is inspired by
[`google/elephant-goldfish-model`](https://github.com/google/elephant-goldfish-model)
at commit `403d888` (Apache-2.0). No upstream prompt text is copied. See
`NOTICE`.
