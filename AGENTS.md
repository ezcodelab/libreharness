<!-- SPDX-License-Identifier: MIT -->
# Agent rules

This repository ships one OpenCode plugin. Procedure lives in `skills/`; this
file is the always-on contract: the commands that must run, the boundaries that
must hold, and the checks that make the rest real.

## Commands

```sh
python3 -m compileall -q bin tests
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest tests.test_tasks -v          # one Python test file
node tests/auto-intake.test.mjs                  # one Node test file
npm run test:node
npm test
node --check src/plugin.js
npm pack --dry-run
npx --yes markdownlint-cli2@0.18.1 '**/*.md'
lychee --offline --include-fragments --exclude-path node_modules '**/*.md'
gitleaks detect --source . --config .gitleaks.toml
```

`npm install` is required once for the Node tests, because `src/plugin.js`
imports `@opencode/plugin`. The Python suite needs no third-party package.

## Boundaries

- Linux, Node 20 or newer, Python 3.10 or newer. Standard library and Node
  built-ins only; a new dependency needs an operator decision.
- `src/plugin.js` registers commands, agents, and skills from `commands/`,
  `agents/`, and `skills/`. `plugins/` holds the hook modules.
- `HARNESS_HOME` is the package root. `HARNESS_STATE` is mutable local state,
  defaulting to `~/.local/state/libreharness` with mode 700.
- Never commit, log, print, or embed secrets, tokens, keys, or PII.
- Never mutate production systems, live data, or shared infrastructure without
  explicit approval in the current turn.
- Never push to `main` or force-push shared history. GitHub is canonical for this
  repository; Gitea is a read-only mirror.
- Do not weaken, delete, or bypass a test, gate, permission, or safety check to
  make a change pass.
- Protected paths need an operator merge: `.github/workflows/`, `.gitleaks.toml`,
  `AGENTS.md`, `SECURITY.md`, `package.json`, `bin/tasks.py`, `bin/jev_*.py`.
- Trivial edits (typo, one line, pure copy) skip the workflow. Everything else
  enters through `skills/engineering-loop/SKILL.md`.
- A user-visible change updates `CHANGELOG.md`.

## Named principles

Name the principle and the decision it changed. These words steer.

- **Laziness protocol.** Delete before you add. Ship the smallest complete change.
- **Foundational thinking.** Choose the data shape before writing the logic.
- **Model the domain.** One structure beats scattered conditionals and flags.
- **Boundary discipline.** Parse and validate at the edge; trust internal types.
- **Type system discipline.** Make illegal states unrepresentable.
- **Subtract before you add.** Remove dead weight, then build on the smaller base.
- **Fix root causes.** Trace to the first wrong state. A guard is a fix only when
  that state is legitimate.
- **Prove it works.** Check the real artifact, not a proxy or "it compiles".
- **Sequence verifiable units.** One checkable unit per commit.
- **Test behavior, not implementation.**
- **Explain the number.** Name the limiter before you report a measurement.
- **Encode lessons in structure.** After the same correction twice, fix it with a
  type, lint, test, or script. Docs last.
- **Guard the context window.** Route bulk reads to subagents; keep summaries.
- **Never block on the human** for reversible work. Pause only at irreversible
  actions and genuine ambiguity.

## Skills

Load on demand. The router picks the playbook; this table is the map.

| Skill | Use |
|---|---|
| `engineering-loop` | Entry point for any non-trivial change |
| `goal`, `work-queue` | Multi-deliverable or durable work |
| `no-comments` | Before review: remove comment alibis |
| `unslop` | Prose: replies, PR bodies, docs, commit messages |
| `correct` | Repeated mistake classes become checks |
| `verification` | Prove behavior on the real artifact |
| `state-audit` | Queues, retries, locks, lifecycle paths |
| `shipping` | Ready PR, CI, independent verdict, merge |
| `parallel-lanes`, `ui-design` | Parallel slices, interface work |

## Rule enforcement

| Rule | Check |
|---|---|
| Secrets and private markers stay out of the tree | `gitleaks detect --source . --config .gitleaks.toml` |
| Tasks close only with a claim, checked acceptance, and real evidence | `python3 -m unittest tests.test_tasks -v` |
| Skill budget, ASCII prose, comment discipline, and this file's size hold | `node tests/harness-ratchets.test.mjs` |
| Review protocol, blast radius, and state audits stay wired | `node tests/review-protocol.test.mjs` |

Per-rule history and new encodings live in
`skills/correct/references/rule-ledger.md`. `/close` and `/tune` append there and
never add rows to this table.
