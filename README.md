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
  state audits, UI design, unslop, verification, and the work queue.
- Agents for exploration, implementation, integration, and independent
  challenge.
- Commands for intake, briefs, lanes, takeover, review, close, handoff, design
  review, and tuning.
- Two local plugins: automatic task intake and a goal watcher.
- Jev, an optional advisory reviewer that returns structured answers about a
  diff, a plan, or a close state.

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
   to auth, secrets, data, or a public API gets a closer look. Jev is one input,
   never the deciding gate.

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

The default state directory is `~/.local/state/libreharness`, created with mode
700. Upgrade by changing the version and reloading OpenCode.

Full install, state layout, configuration, and upgrade notes are in
[docs/reference.md](docs/reference.md#install).

## One path

Describe the outcome in OpenCode. Auto-intake creates the task, and the agent
runs brief, implement, verify, review, close, and ship. You do not need to type
a slash command. The harness opens a ready pull request, waits for CI, requires
an independent verdict, and merges only the verified patch. It stops at
human-only gates such as secrets, production, releases, force-pushes, and CI
changes.

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

## Jev

Jev sends a task and a diff, a goal plan, or a close state to a typed-question
endpoint. It returns scores on seven quality axes, a ship/scope/test verdict, a
plan gap, or a close-triage lesson. The answers are structured, so they can be
compared instead of read as a chat opinion.

Jev is optional and advisory. It never merges, closes, or blocks a task by
itself. Set `JEV_MODEL` to a model your endpoint offers; a missing key is a skip
at the workflow level. See [the reference](docs/reference.md#jev).

## Documentation

[docs/reference.md](docs/reference.md) is the operator reference: install,
concepts, workflow, commands, skills, agents, plugins, Jev, security, and CI.

Project history is in [CHANGELOG.md](CHANGELOG.md).

## Requirements

Linux, OpenCode 2.x, Node 20 or newer, and Python 3.10 or newer. A model
provider of your choice. Jev needs an endpoint and a key only when you use it.

## License

Code in `bin/`, `plugins/`, `tests/`, `agents/`, `commands/`, `skills/`, `src/`,
and JSON configuration is MIT. Narrative documentation under `docs/**/*.md` is
CC BY 4.0; code snippets are MIT. See [LICENSE](LICENSE), [NOTICE](NOTICE), and
[docs/LICENSE](docs/LICENSE).
