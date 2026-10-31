<!-- SPDX-License-Identifier: MIT -->

# LibreHarness

A durable work queue, a risk-scaled engineering workflow, reusable agents,
commands, and skills, local OpenCode plugins, and an advisory typed-question
reviewer called Jev.

**Status: 1.0.0-rc.1, local release candidate. Benchmark unrun.**
This tree has not been published. No performance, cost, or quality claim is
backed by a benchmark yet. Treat the harness as a workflow to evaluate, not as
a proven improvement.

## What it is

The harness gives an OpenCode user a small, inspectable system for work that
outlives one chat:

- A Markdown work queue with tasks, goals, dependencies, lanes, evidence, and
  a generated board.
- A workflow that scales process to risk: trivial changes skip the queue,
  nontrivial changes get a brief, a review, and evidence.
- Five portable skills: engineering loop, goal loop, parallel lanes, UI
  design, and work queue.
- Agents for exploration, implementation, integration, and independent
  challenge.
- Commands for goal intake, briefs, lanes, review, integration, close,
  handoff, and tuning.
- Four local plugins: automatic task intake, close reminder, continuation
  watcher, and an advisory security scan.
- Jev, a first-class advisory layer that asks typed questions about a diff, a
  plan, or a close state and returns structured answers.

The queue is stdlib Python plus POSIX file locking. There is no database, no
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

## One-command install

```sh
npx libreharness init
```

The guided installer asks for the OpenCode config and state directories, copies
the runtime, creates `opencode.json` only when none exists, and runs the
environment check. For an unattended install, add `--yes`.

Until the npm package is published, use the checkout directly:

```sh
node bin/libreharness.js init
```

The installer does not choose a provider or model. Start OpenCode and choose
one with `/models`.

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

The small B1-B8 suite is a local regression supplement only. Its
`bench/score.py` is not the public headline. See
[docs/benchmark-tools.md](docs/benchmark-tools.md) and
[bench/protocol.md](bench/protocol.md). A two-task pilot is recorded in
[bench/pilot-2026-10-30.md](bench/pilot-2026-10-30.md); it is adapter-only, not
a harness result, and shows no quality delta. The earlier adapter overlay upload
was dead code; the `setup()` fix now uploads it, and a post-fix one-task smoke
passed. The full dataset is still unrun.

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

## Status and support

| Item | Status in 1.0.0-rc.1 |
|---|---|
| Release | Local candidate, not published |
| Benchmark | Not run; no results are shipped |
| Platform | Linux and macOS |
| Windows | Not supported in 1.0.0; 1.1 preview planned |
| Python | 3.10 or newer |
| Node | 20 or newer, for plugin tests and optional plugins |
| OpenCode | 2.x |
| CI | Workflows are present in the tree; publication CI has not been verified |
| Support | Best effort, no SLA, no bounty |

The supported scope is the queue, commands, agents, five skills, the four
bundled local plugins, the Jev client, and the documented install path.
Third-party plugins, custom providers, custom Jev adapters, Windows, and
private knowledge integrations are outside 1.0.0 support.

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

## Non-goals

- A hosted service, model proxy, model provider, or account system.
- Publishing a private knowledge base, personal tasks, transcripts, logs, or
  calibration data.
- Replacing OpenCode or becoming a general multi-agent framework in 1.0.0.
- Windows support in 1.0.0.
- A claim that the harness is faster, cheaper, or better before the benchmark
  protocol has been run and reviewed.
- A guarantee that Jev's advice is correct. It is evidence, not a gate.

## Documentation

Start at [docs/README.md](docs/README.md). For a clean install, read
[docs/install.md](docs/install.md). For the first task, read
[docs/quickstart.md](docs/quickstart.md). For the design rationale, read
[docs/design-notes.md](docs/design-notes.md).
