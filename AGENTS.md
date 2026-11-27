<!-- SPDX-License-Identifier: MIT -->
# Agent rules

This repository ships one OpenCode plugin. Procedure lives in `skills/`; this
file is the always-on contract: the commands that must run, the boundaries that
must hold, and the checks that make the rest real.

## Commands

```sh
npm run tools:install
npm run check:local
npm test
python3 -m unittest tests.test_tasks -v          # one Python test file
node tests/auto-intake.test.mjs                  # one Node test file
npm run lint:md
npm run lint:links
npm run lint:secrets
npm run lint:shell
npm run lint:workflows
```

`npm install` and `npm run tools:install` are required once for contributor
checks. The second command fetches checksum-verified lychee, gitleaks,
actionlint, and shellcheck into `$XDG_CACHE_HOME/libreharness/tools` for Linux
x64 and arm64. `npm run check:local` runs the same syntax, test, package, and
lint set as CI. The Python suite needs no third-party package.

## Boundaries

- Linux, Node 20 or newer, Python 3.10 or newer. Standard library, Node
  built-ins, and the OpenCode plugin runtime. Dev-only dependencies stay pinned,
  and repository checks fetch checksum-verified upstream binaries without
  bundling them into the plugin.
- `src/plugin.js` registers commands, agents, and skills from `commands/`,
  `agents/`, and `skills/`. `plugins/` holds the hook modules.
- `HARNESS_HOME` is the package root. `HARNESS_STATE` is mutable local state,
  defaulting to `~/.local/state/libreharness` with mode 700.
- Harness operations come from the plugin tools `tasks`, `comment_audit`, and
  `pr_guard`; never call a clone path or a config-bin fallback.
- Never commit, log, print, or embed secrets, tokens, keys, or PII.
- Never mutate production systems, live data, or shared infrastructure without
  explicit approval in the current turn.
- Never push to `main` or force-push shared history. GitHub is canonical for this
  repository; Gitea is a read-only mirror.
- Do not weaken, delete, or bypass a test, gate, permission, or safety check to
  make a change pass.
- No path is protected. A ready PR with green required checks and a recorded
  review artifact auto-merges; an irreversible deploy, data deletion, live secret
  rotation, or force-push still needs explicit approval.
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

Load on demand. The map lives in [skills/README.md](skills/README.md); the
router picks the playbook.

## Rule enforcement

| Rule | Check |
|---|---|
| Secrets and private markers stay out of the tree | `npm run lint:secrets` |
| Tasks close only with a claim, checked acceptance, and real evidence | `python3 -m unittest tests.test_tasks -v` |
| Skill structure and ASCII prose hold | `node tests/harness-ratchets.test.mjs` |
| Comment and suppression debt fails closed | `npm run lint:comments` |
| Review artifacts, policy paths, and state audits stay wired | `node tests/harness-ratchets.test.mjs` |

Per-rule history and new encodings live in
`skills/correct/references/rule-ledger.md`. `/close` and the periodic tune in
`correct` append there and never add rows to this table.
