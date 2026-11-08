<!-- SPDX-License-Identifier: MIT -->

# LibreHarness

A durable work queue, a risk-scaled engineering workflow, reusable agents,
commands, and skills, local OpenCode plugins, and an advisory typed-question
reviewer called Jev.

## What it is

The harness gives an OpenCode user a small, inspectable system for work that
outlives one chat:

- A Markdown work queue with tasks, goals, dependencies, lanes, evidence, and
  a generated board.
- A workflow that scales process to risk: trivial changes skip the queue,
  nontrivial changes get a brief, a review, and evidence.
- Seven portable skills: engineering loop, goal loop, parallel lanes, state
  audit, UI design, verification, and work queue.
- Agents for exploration, implementation, integration, and independent
  challenge.
- Commands for queue inspection, goal intake, briefs, lanes, takeover, review,
  state audit, close, handoff, design review, and tuning.
- Four local plugins: automatic task intake, close reminder, a goal watcher for
  continuation and closable-goal reminders, and an advisory security scan.
- Jev, a first-class advisory layer that asks typed questions about a diff, a
  plan, or a close state and returns structured answers.

The queue is stdlib Python plus Linux file locking. There is no database, no
server, and no third-party Python package. Local plugins use Node built-ins.

## Why it exists

Chat sessions lose context, and "done" often means "the model said so". The
harness makes three things durable:

1. **State.** A task is a file. It survives a session, a model switch, and a
   crash. The board is generated from the files, not hand-maintained.
2. **Evidence.** A task cannot be marked done with "tests pass" or "none". It
   needs a command and result, a measured check, or an explicit `[T]` with a
   plan.
3. **Review proportional to risk.** A typo does not need a committee. A change
   to auth, secrets, data, or a public API gets a closer look. Jev is one
   input, never the deciding gate.

## Choose the next action

| You are about to... | Start with |
|---|---|
| Nontrivial work, or you are unsure | `/goal` |
| Continue a task | `/brief <task-id>` |
| Run independent slices | `/goal go` auto-lanes; `/lane` only for manual isolation |
| Review a diff | `/review <task-id>` (a check, not a finish step) |
| Audit stateful code | `/state-audit <path>` |
| Resume after a pause | `/takeover <task-id>` |
| Finish a task or goal | `/close <task-id>` (integrates goal lanes) |
| Review a UI | `/design-review` |
| Prove real app behavior | `verification` skill |
| Clean up the workflow | `/tune` |

The full operator guide, including every skill, command, agent, plugin, and Jev
client, is [When to use what](docs/when-to-use.md).

## Install as a plugin (recommended)

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    {
      "package": "libreharness@1.1.0",
      "options": { "state": "~/.local/state/libreharness" }
    }
  ]
}
```

1.1.0 is prepared but not yet published. Until then, use the checkout path or
the offline installer below.

The plugin registers commands, agents, and skills from the package, so an
update is a package version change rather than a file copy.

## Offline copy install

```sh
npx libreharness init
```

The guided installer asks for the OpenCode config and state directories, copies
the runtime, creates `opencode.json` only when none exists, and runs the
environment check. For an unattended install, add `--yes`.

The full walkthrough is in [docs/quickstart.md](docs/quickstart.md). The manual
path is in [docs/install.md](docs/install.md).

## Benchmark

The public headline is **Terminal-Bench 2.0 resolution rate** run through
Harbor. Harbor already supports OpenCode, reports tokens and cost, and has a
public leaderboard and an OpenCode entry:

```sh
uv tool install harbor
harbor run -d terminal-bench@2.0 -a opencode -m <provider>/<model>
```

The before baseline is plain OpenCode on the same tasks, model, and
environment. The after result uses the local Harbor adapter
`harbor_agent.opencode_agent:OpenCodeLibreHarness`, which installs the workflow
files in the sandbox. Cost, tokens, and wall time are reported alongside
resolution rate, not blended into a score.

The benchmark code for the EGM and Superpowers comparison is in
[bench/](bench/); the protocol and falsification rules are in
[docs/benchmark-proof.md](docs/benchmark-proof.md). No result is shipped with
this tree.

## Jev, the advisory layer

Jev sends a task and a diff, a goal plan, or a close state to a typed-question
endpoint. It returns scores on seven quality axes, a ship/scope/test verdict, a
plan gap, or a close-triage lesson. The answers are structured, so they can be
compared and calibrated instead of read as a chat opinion.

Jev is advisory. It never merges, closes, or blocks a task by itself. The
operator or reviewing agent decides.

The client does not hardcode a model. Set `JEV_MODEL` to a model your endpoint
offers. `JEV_ENDPOINT` and `JEV_KEY_FILE` are configurable. A missing key is a
skip at the workflow level: the quickstart and the full test suite do not need
one. See [docs/jev.md](docs/jev.md).

## License

| Path | License |
|---|---|
| Code in `bin/`, `plugins/`, `tests/`, `agents/`, `commands/`, `skills/`, and JSON configuration | MIT |
| Narrative documentation under `docs/**/*.md` | CC BY 4.0 |
| `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `GOVERNANCE.md`, `CHANGELOG.md` | MIT |
| `LICENSE` | MIT license text |
| `NOTICE` | Factual notices |
| `docs/LICENSE` | CC BY 4.0 legal code for `docs/**/*.md` |

Code snippets inside documentation are MIT. The surrounding prose is CC BY
4.0. See [LICENSE](LICENSE), [NOTICE](NOTICE), and [docs/LICENSE](docs/LICENSE).

## Documentation

Start at [docs/README.md](docs/README.md). For the next action, read
[docs/when-to-use.md](docs/when-to-use.md). For a clean install, read
[docs/install.md](docs/install.md). For the first task, read
[docs/quickstart.md](docs/quickstart.md). For the design rationale, read
[docs/design-notes.md](docs/design-notes.md).
