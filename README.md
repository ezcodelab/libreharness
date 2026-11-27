<!-- SPDX-License-Identifier: MIT -->

# LibreHarness

A durable work queue and a risk-scaled engineering workflow for coding agents.

## What it is

LibreHarness gives an agent user a small, inspectable system for work that
outlives one chat:

- A Markdown work queue with tasks, goals, dependencies, lanes, evidence, and a
  generated board.
- A workflow that scales process to risk: trivial changes skip the queue;
  nontrivial changes get a brief, a review, and evidence.
- Portable skills, mapped in [skills/README.md](skills/README.md), with
  `engineering-loop` as the entry point.
- A playbook router that turns a request into one checklist: investigation, bug
  fix, feature, refactoring, perf, hillclimb, autonomous multi-phase, or a
  repeated-mistake sweep.
- Structural ratchets that fail on non-ASCII punctuation, an unreferenced
  workaround comment, or a repeated always-on rule.
- Agents for exploration, implementation, integration, and independent
  challenge.
- Commands for intake, briefs, lanes, takeover, review, close, handoff, design
  review, and tuning.
- Three local plugins: automatic task intake, a goal watcher, and a usage
  ledger for cost-per-verified-task measurement.

The queue is stdlib Python with native Linux, macOS, and Windows locking. There
is no database, no server, and no third-party Python package. The only runtime
Node dependency outside the OpenCode adapter is the pinned MCP server SDK.

## Why it exists

Chat sessions lose context, and "done" often means "the model said so". The
harness makes three things durable:

1. **State.** A task is a file. It survives a session, a model switch, and a
   crash. The board is generated from the files.
2. **Evidence.** A task cannot be marked done with "tests pass" or "none". It
   needs a command and result, a measured check, or a tracked `[T]` with a plan.
3. **Review proportional to risk.** A typo does not need a committee. A change
   to auth, secrets, data, or a public API gets a closer look. Deterministic
   checks and a review artifact are the default gate; a model second opinion is
   an explicit operator request, never the deciding gate.

## Install

Choose one native route per host. Do not install both the plugin and a copied
skill tree in the same host.

| Host | Install |
|---|---|
| OpenCode | Add `libreharness@2.1.0` to the global `plugins` array in `~/.config/opencode/opencode.json` and keep the four agent stubs |
| Claude Code | `claude plugin marketplace add ezcodelab/libreharness` then `claude plugin install libreharness@libreharness` |
| Codex | `codex plugin marketplace add ezcodelab/libreharness` then `codex plugin add libreharness@libreharness` |
| GitHub Copilot CLI | `copilot plugin marketplace add ezcodelab/libreharness` then `copilot plugin install libreharness@libreharness` |
| Cursor | In Customize, add the GitHub repository as a plugin marketplace, then install LibreHarness |

The native plugin exposes the canonical skills and three MCP tools. The MCP
server starts from the installed npm package, not from the plugin checkout. Its
first start downloads `libreharness@2.1.0` through `npx`; an air-gapped machine
must preinstall that exact package through an approved registry mirror.

Only hosts with a passing certificate in
[docs/certification/SUPPORT.md](docs/certification/SUPPORT.md) are supported.
A standards-compatible client without a certificate is untested. Certification
uses a host-driven install, skill and tool discovery, a real tool call, and the
recorded journey in
[docs/certification/manual-procedure.md](docs/certification/manual-procedure.md).

The four OpenCode agent stubs are required. Add a model to a stub for per-agent
routing, or set the optional `agentModels` plugin option. Use exact models
available in the operator's provider. From a checkout, run
`npm install --omit=dev --no-audit --no-fund` and use the absolute plugin path.

State lives under `%LOCALAPPDATA%\libreharness` on Windows,
`~/Library/Application Support/libreharness` on macOS, or the existing XDG state
directory on Linux. OpenCode uses its `state` option. Native MCP hosts use
`HARNESS_STATE`.

Full install, state layout, configuration, and upgrade notes are in
[docs/reference.md](docs/reference.md#install).

## One path

Describe the outcome in any certified host. The engineering loop creates or
claims the task, then runs brief, implement, verify, review, close, and ship.
OpenCode also provides automatic pre-prompt intake and goal watching. You do not
need to type a slash command. The harness records observed checks and the exact
HEAD, opens a ready pull request, waits for required CI, and merges only the
reviewed head. It still stops at irreversible actions such as a production
deploy, data deletion, a live secret rotation, or a force-push.

Slash commands remain escape hatches when you want to intervene directly:

| You are about to... | Use |
|---|---|
| Let the harness run a request | Just describe it; no command required |
| Intervene in a task or goal | `/goal <request-or-id>` |
| Continue or resume a task | The `work-queue` brief and resume procedures |
| Run independent slices | Auto-lanes; `tasks lane` only for manual isolation |
| Review a diff | `/review <task-id>` |
| Audit stateful code | The `state-audit` skill |
| Finish a task or goal | `/close <task-id>` |
| Unslop one UI surface with one A/B choice | The `unslop-ui` skill |
| Review a UI | The `ui-design` skill and its review reference |
| Prove real app behavior | The `verification` skill |
| Clean up the workflow | The `correct` skill's periodic tune |

## Documentation

[docs/reference.md](docs/reference.md) is the operator reference: install,
concepts, workflow, commands, skills, agents, plugins, security, and CI.

Project history is in [CHANGELOG.md](CHANGELOG.md). Contributions are welcome;
see [CONTRIBUTING.md](CONTRIBUTING.md) and the issue and pull request templates
in `.github/`.

## Requirements

Linux, macOS, or Windows. Node 20 or newer, Python 3.10 or newer, and Git. A
certified host is required for support. The authenticated GitHub CLI is required
to ship pull requests; without it, `pr_guard` fails closed and the task must
explicitly mark shipping inapplicable. Repository contributors get the pinned
check tools through npm without system installs; a model provider is still your
choice.

## License

All code, documentation, and snippets are MIT. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
