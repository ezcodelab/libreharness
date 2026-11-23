<!-- SPDX-License-Identifier: MIT -->

# LibreHarness

A durable work queue and a risk-scaled engineering workflow for OpenCode.

## What it is

LibreHarness gives an OpenCode user a small, inspectable system for work that
outlives one chat:

- A Markdown work queue with tasks, goals, dependencies, lanes, evidence, and a
  generated board.
- A workflow that scales process to risk: trivial changes skip the queue;
  nontrivial changes get a brief, a review, and evidence.
- Portable skills for the engineering loop, goals, parallel lanes, shipping,
  state audits, UI design, no-comments, unslop, correct, verification, and the
  work queue.
- A playbook router that turns a request into one checklist: investigation, bug
  fix, feature, refactoring, perf, hillclimb, autonomous multi-phase, or a
  repeated-mistake sweep.
- Structural ratchets that fail on a skill over budget, non-ASCII punctuation,
  an unreferenced workaround comment, or an oversized always-on rule file.
- Agents for exploration, implementation, integration, and independent
  challenge.
- Commands for intake, briefs, lanes, takeover, review, close, handoff, design
  review, and tuning.
- Two local plugins: automatic task intake and a goal watcher.

The queue is stdlib Python plus Linux file locking. There is no database, no
server, and no third-party Python package. The Node plugins use built-ins only.

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

Add the package to the global `plugins` array in
`~/.config/opencode/opencode.json`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["libreharness@2.0.0"],
  "agents": {
    "devils-advocate": {},
    "explore": {},
    "implementer": {},
    "integrator": {}
  }
}
```

The four agent stubs are required. The plugin fills each one's prompt, mode, and
permissions; add a model to a stub for per-agent routing. From a checkout, use
the absolute path instead of the npm name.

OpenCode loads global and project `AGENTS.md` files natively. The plugin does not
inject instructions, so the LibreHarness contract stays scoped to this workspace.

The default state directory is `~/.local/state/libreharness`, created with mode
700. Upgrade by changing the version and reloading OpenCode.

Full install, state layout, configuration, and upgrade notes are in
[docs/reference.md](docs/reference.md#install).

## One path

Describe the outcome in OpenCode. Auto-intake creates the task, and the agent
runs brief, implement, verify, review, close, and ship. You do not need to type
a slash command. The harness records observed checks and the exact HEAD, opens a
ready pull request, waits for required CI, and merges only the reviewed head. No
path is protected. It still stops at irreversible actions such as a production
deploy, data deletion, a live secret rotation, or a force-push.

Slash commands remain escape hatches when you want to intervene directly:

| You are about to... | Use |
|---|---|
| Let the harness run a request | Just describe it; no command required |
| Intervene in a task or goal | `/goal <request-or-id>` |
| Continue a task | `/brief <task-id>` |
| Run independent slices | Auto-lanes; `/lane` only for manual isolation |
| Review a diff | `/review <task-id>` |
| Audit stateful code | `/state-audit <path>` |
| Resume after a pause | `/takeover <task-id>` |
| Finish a task or goal | `/close <task-id>` |
| Review a UI | `/design-review` |
| Prove real app behavior | `verification` skill |
| Clean up the workflow | `/tune` |

## Documentation

[docs/reference.md](docs/reference.md) is the operator reference: install,
concepts, workflow, commands, skills, agents, plugins, security, and CI.

Project history is in [CHANGELOG.md](CHANGELOG.md). Contributions are welcome;
see [CONTRIBUTING.md](CONTRIBUTING.md) and the issue and pull request templates
in `.github/`.

## Requirements

Linux, OpenCode 2.x, Node 20 or newer, and Python 3.10 or newer. A model
provider of your choice.

## License

All code, documentation, and snippets are MIT. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
