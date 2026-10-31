<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Documentation

This index describes the public documentation set for LibreHarness
1.0.0-rc.1.

Status: local release candidate. The benchmark has not been run. No document
here makes a performance claim.

## Start here

| Document | What it answers |
|---|---|
| [Install](install.md) | One-command `npx libreharness init`, guided and unattended paths, upgrade, and manual fallback |
| [Quickstart](quickstart.md) | Create, claim, review, and close one task after install |
| [Concepts](concepts.md) | What a task, goal, lane, handoff, evidence, review, and close mean |
| [Workflow](workflow.md) | How the pieces fit together, with a worked example and the evidence gate |

## Reference

| Document | What it answers |
|---|---|
| [Command reference](command-reference.md) | Every slash command and queue CLI argument |
| [Skills](skills.md) | The five bundled skills, their triggers, the budget, and how to add one |
| [Plugins](plugins.md) | The four local plugins, their environment, failure modes, and disable switches |
| [Model routing](model-routing.md) | Roles, provider-agnostic configuration, static matrix, and cost controls |
| [Skill evaluation](skill-eval.md) | How to run a small with/without experiment before promoting a skill |
| [EGM review](egm-review.md) | What Google's Elephant-Goldfish Model does, what to adopt, and whether the Harbor adapter is still the right integration |
| [Superpowers review](superpowers-review.md) | What Superpowers does, which skills fit, and the four-arm comparison design |
| [Self-improvement pilot](self-improvement-2026-10-31.md) | Four-arm review pilot, Harbor check, and the rejected Superpowers change |
| [Benchmark proof protocol](benchmark-proof.md) | What would make an “objectively best” claim valid, and what would falsify it |
| [Benchmark tool review](benchmark-tools.md) | Why Harbor and Terminal-Bench are the standardized external benchmark |
| [Local benchmark protocol](../bench/protocol.md) | The small B1-B8 regression suite and its pass@1 calculation |

## Jev

| Document | What it answers |
|---|---|
| [Jev](jev.md) | What Jev is, how to configure a key and model, the commands, exit codes, cost, and privacy |
| [Jev adapter](jev-adapter.md) | The typed-question request and response contract, the mock transport, and how to add a provider |
| [Jev calibration](jev-calibration.md) | The ten-diff method, false positives, thresholds, and limitations |

## Trust and operations

| Document | What it answers |
|---|---|
| [Security and privacy](security-privacy.md) | What is stored, what leaves the machine, how secrets are handled, and what is not protected |
| [Process lessons](process-lessons.md) | Dated surprises, costs, rules, and doc updates from completed work |
| [Troubleshooting](troubleshooting.md) | Install, plugin, queue, permission, Jev, and upgrade errors with a next step |
| [FAQ](faq.md) | Short answers to the questions a new user asks first |
| [Design notes](design-notes.md) | Why the queue is Markdown, why the evidence gate exists, rejected alternatives, and the 1.1 and 1.2 previews |

## Project files

| File | Purpose |
|---|---|
| [README](../README.md) | Project overview, quickstart, status, license, and non-goals |
| [CONTRIBUTING](../CONTRIBUTING.md) | Development setup, tests, DCO, and pull request checklist |
| [SECURITY](../SECURITY.md) | Private reporting, supported versions, and Jev key guidance |
| [GOVERNANCE](../GOVERNANCE.md) | Maintainer role, one-way gates, issues, pull requests, and releases |
| [CHANGELOG](../CHANGELOG.md) | Release history and known limitations |
| [NOTICE](../NOTICE) | Copyright, Jev client origin, and dependency boundary |
| [LICENSE](../LICENSE) | MIT license for code and configuration |
| [Documentation license](LICENSE) | CC BY 4.0 legal code for `docs/**/*.md` |

## Reading paths

**New user:** [Install](install.md), then [Quickstart](quickstart.md), then
[Concepts](concepts.md) and [Workflow](workflow.md).

**Evaluator:** [Concepts](concepts.md), [Workflow](workflow.md),
[Security and privacy](security-privacy.md), then [Design notes](design-notes.md).

**Jev user:** [Jev](jev.md), then [Jev adapter](jev-adapter.md) if you need a
custom provider, then [Jev calibration](jev-calibration.md) before trusting a
threshold.

**Contributor:** [CONTRIBUTING](../CONTRIBUTING.md), [Command
reference](command-reference.md), [Skills](skills.md), and
[Plugins](plugins.md).

## Documentation rules

- Plain English. No private home path, hostname, token, or personal data.
- Every relative link resolves.
- Every command is checked against the runtime in this tree.
- A performance claim needs benchmark evidence. Without it, say "unrun".
- Code snippets are MIT. The surrounding prose is CC BY 4.0.
