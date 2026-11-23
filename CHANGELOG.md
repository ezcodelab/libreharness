<!-- SPDX-License-Identifier: MIT -->

# Changelog

## Unreleased

### Instruction budget

- The skill map has one owner, `skills/README.md`; `AGENTS.md`, `README.md`, and
  `docs/reference.md` link to it.
- Instruction ceilings are fixed from the measured post-delete sizes plus two
  lines of slack, and a total budget fails on net growth until a line is
  deleted. The numbers live in `tests/harness-ratchets.test.mjs`.

### Review and shipping

- `/review` records observed exits and the exact HEAD in
  `$HARNESS_STATE/work/reviews/<task-id>.json` through `tasks.py review --run`.
  Close, the review status transition, and shipping reject a missing, stale,
  failed, mismatched, or UNVERIFIED artifact.
- A task cannot be claimed without a structured `Data shape` line and one
  allowlisted `Verify` command in its Plan.
- Remove the routine model review. A second opinion is an explicit operator
  request and can only downgrade the artifact with `--unverify`.
- Remove the `jev_plan` and `jev_triage` clients, the nightly model check, and
  agent-facing Jev references. `bin/jev_review.py` remains out-of-band only.
- Remove `tests/review-protocol.test.mjs`; the harness ratchet now rejects
  agent-facing Jev and stale review-policy phrases by path.

### Instructions

- Native OpenCode instruction discovery now owns global and project `AGENTS.md`.
  The plugin no longer injects the LibreHarness contract into every session.
- Auto-intake routes reused tasks and queue-helper failures through
  `engineering-loop`, and blocks intake with a workflow error when the skill or
  a playbook section is missing.

### Review

- Prefer empirical and deterministic verification over abstract adversarial
  review. Spend the tokens on running the artifact, the reproduction, the tests,
  or the formal check. Use the reviewer sparingly, as a second opinion.
- One abstract review pass per change, not a loop. Anchor it to the goals and
  invariants so it does not nitpick or steer the author away from the intent.
  The author evaluates each finding instead of accepting it sycophantically.
  If a blocker survives one fix, escalate rather than starting another round.

### 🛡 Enforcement

- Remove every protected path and the operator-merge stop. A ready PR with
  green required checks and a recorded review verdict auto-merges. Irreversible
  actions still pause: production deploy, data deletion, live secret rotation,
  and force-push.

## 2.1.0 - 2026-11-19

Route non-trivial work through one playbook router and make the harness's own
instructions enforceable. Each change is one green commit.

### 🚀 Features

- `engineering-loop` is now the single entry point. It matches a request to one of
  eight playbooks (`investigation`, `bug-fix`, `feature`, `refactoring`, `perf`,
  `hillclimb`, `autonomous-multiphase`, `correct`), copies the checklist from
  `skills/engineering-loop/references/playbooks.md` into the todo list, and falls
  back to `feature` or `investigation` with a stated reason.
- Add `no-comments`: remove narration, commented-out code, dead markers, and
  workaround justifications, then reshape each claimed constraint into a type,
  lint, test, or runtime check. An unreferenced workaround comment now blocks
  review.
- Add `correct`: mine repeated mistakes and fix each at the highest level that
  works, with a failing check on the real past mistake. Rows go to
  `skills/correct/references/rule-ledger.md`.
- `plugins/auto-intake.js` exports `routePrompt(text)` and states the selected
  playbook in the intake notice. It loads `goal` only for multi-step or
  unattended prompts, and free text never selects `correct`.
- Add a project-local `verify-libreharness` skill that drives `plugin.setup`, the
  intake hook, and the queue close-out against a disposable state directory, then
  reports what remains unverified.
- `unslop` is now prose-only: replies, PR bodies, commit messages, and docs. Code
  cleanup moved to `engineering-loop` and `correct`.

### 🛡 Enforcement

- Add `tests/harness-ratchets.test.mjs`, wired into `npm test`. It fails on a
  `SKILL.md` over 120 lines, an em dash or curly quote in scoped instruction
  files, an unreferenced workaround comment, an oversized `AGENTS.md` or
  enforcement table, a broken relative link, a hollow playbook section, and a
  missing router, brief, implementer, review, or intake contract.
- `AGENTS.md` drops to a commands, boundaries, principles, and four-row
  enforcement table. Task routing leaves the always-on file.
- The plugin's context deduplication key moves from `## Task scale` to
  `## Rule enforcement`, so the local config can stay machine-local.

## 2.0.0 — 2026-11-18

Slim the repository to the pstack-shaped core: the queue, workflow, skills,
agents, commands, two local plugins, and Jev. Removed experiment and vendored
assets, native-duplicated scripts, and most narrative documentation.

### 💥 Breaking

- Install as an OpenCode plugin only. The `npx libreharness init` installer and
  the copied-runtime layout are removed. Add `libreharness@2.0.0` to the
  `plugins` array and reload.
- Remove `bench/`, `harbor_agent/`, `profiles/`, `templates/`, `scripts/`, and
  the benchmark and experiment documentation. Benchmark evidence is no longer
  shipped in-tree.
- Remove the `close-reminder` and `security-guard` plugins. Protect secret files
  with native OpenCode permissions or a dedicated guard plugin.
- Remove the custom CI and review helpers (`check_mirror`, `check_spdx`,
  `comment_audit`, `docs_lint`, `doctor`, `pr_policy`, `pr_watch`,
  `scan_private`, `sync_gitea_gate`, `verify_pr.sh`). CI now uses
  `markdownlint-cli2`, `lychee`, `gitleaks`, `shellcheck`, and `actionlint`;
  shipping uses `gh pr checks` and `gh pr merge`.
- Consolidate the documentation set into `README.md` and `docs/reference.md`.
- Relicense documentation under MIT and remove `docs/LICENSE`; code,
  documentation, and snippets now share one license.
- Remove `opencode.example.json`; the plugin config in `README.md` is the single
  example.
- Remove `GOVERNANCE.md` and `CODE_OF_CONDUCT.md`.

### 🚀 Features

- Keep the durable Markdown queue, evidence gate, goals, lanes, review, close,
  and Jev.
- Add the `unslop` skill: a read-only audit of the patterns agents copy, a
  ratchet plan, and one-pattern fixes that delete the old example first.
- Harness agents no longer ask for shell command permission on reversible work.
  Unattended runs stop only at one-way doors, secrets or production, missing
  decisions or credentials, or ambiguous acceptance.

## 1.2.0 — 2026-11-16

Verified delivery automation: one path from a request to a merged, verified
patch.

### 🚀 Features

- Verification has create, maintain, and formal modes. State audits now emit a
  Mermaid statechart and maintain `docs/state-machines.md`.
- Comment discipline adds a stdlib audit and non-blocking review guidance for
  narration, workaround justifications, and stale comments.
- The shipping skill and `bin/pr_watch.py` gate a ready PR on an independent
  verifier PASS, the current head SHA, green CI, no conflicts, and evidence.
- Auto-intake runs the default path without a required user-typed slash
  command: brief, implement, verify, review, close, and ship.
- The CI link check excludes `node_modules`, so the new plugin dependency does
  not fail every matrix cell.

### 🧭 Behaviour

- The shipping gate accepts only a strict `PASS <sha>` or `PASS+NOTES <sha>`
  verdict and only `SUCCESS` CI conclusions. Pending, skipped, neutral, and
  failed checks block.
- Queue documentation now matches the real claimable states: `inbox`, `ready`,
  and `blocked --force`.
- Slash commands remain manual forms; the normal path starts from a request.

### ⚠️ Limits

- A provider/model is still chosen by the user; the harness does not choose one.
- The live shipping path was proven on PR #2; branch protection remains the
  outer merge gate.

## 1.1.0 — 2026-11-08

OpenCode V2 plugin distribution: commands, agents, and skills load from the
package instead of being copied into the config.

### 🚀 Features

- The npm package exports a V2 server plugin. It registers the bundled
  commands and seven skills, and updates the four agents declared under
  `agents` in `opencode.json`.
- The main plugin bundles `auto-intake`, `close-reminder`, `goal-watch`, and
  `security-guard`; no separate plugin files are needed.
- The plugin sets `HARNESS_HOME` and `HARNESS_STATE`; the existing Python CLI
  commands work unchanged.
- Model overrides in `opencode.json` are preserved when the plugin updates
  agent prompts and permissions.
- The four harness agents allow normal reads with `read * allow`. Secret-file
  policy stays in one layer (EnvSitter, `cc-safety-net`, or one global rule),
  not repeated in every agent.
- The plugin updates config-defined agents by id; it does not use `editor.get`
  as an existence gate.

### 🧭 Behaviour

- Plugin install is the no-drift path: update the package version and reload.
- The offline copy installer remains available, but normal installs no longer
  need it.
- State defaults to a real `~/.local/state/libreharness` directory with mode
  700. The plugin does not follow a `HARNESS_STATE` environment variable or a
  symlink; a knowledge base such as a brain stays separate.

### ⚠️ Limits

- OpenCode V2 can update an existing agent from a plugin but cannot create
  one. The four agent stubs must exist under `agents` in `opencode.json`.
- The npm package needs a provider/model chosen by the user; the harness does
  not choose one.

## 1.0.0 — 2026-11-04

First public npm release: a Linux-only, OpenCode-only harness for durable
tasks, risk-scaled engineering, reusable agents and skills, local plugins, and
advisory Jev review.

### 🚀 Features

- A seven-question benchmark number checklist in `docs/benchmark-proof.md`:
  limiter, tuned sides, physical limits, errors, repeatability, end-to-end
  relevance, and whether the work happened.
- Eight named principles in `AGENTS.md`, explained with triggers and examples
  in `docs/principles.md`.
- A `verification` skill that generates a project-local `verify-<app>` skill
  with launch, doctor, drive, evidence, cleanup, helpers, and a feature map,
  then proves it once end to end.
- A one-safety-fact check in `/review` and `devils-advocate`: name the fact the
  change is safe because of and prove it by running code, or mark it unverified.
- Structural correction in `/tune` and `/close`: fix repeated mistakes at the
  highest level that works and prove the check on a past mistake.
- `tasks.py reap` removes clean worktrees whose task is review/done/abandoned
  and whose branch is merged into another branch; active, dirty, or unmerged
  lanes are retained.
- `goal-watch` reminds once per session when an active goal is closable. The
  operator can reply "close now" to run `/close` or "later" to keep it open; the
  plugin never closes a goal itself.

### 🛡️ Security

- CI uses a pinned gitleaks binary instead of the organization-licensed action.
  Synthetic secret shapes in guard and benchmark fixtures are explicitly
  allowlisted; real code and history remain scanned.

### 🐛 Fixes

- Jev error text now names `~/.config/opencode/jev.key`, matching the resolver.

### 🧭 Behaviour

- `/close` is the single finish command. For a goal it integrates reviewed
  lanes, runs the final review, reaps clean worktrees, records the lesson, and
  closes with evidence. `/review` is a check; `/tune` is periodic maintenance.
- Goal start auto-creates up to three lanes for ready children; `/lane` is a
  manual escape hatch.

### 🧹 Removed

- The operator-facing `/harvest` and `/integrate` commands. Lesson capture is
  part of `/close`; integration is part of `/close` for a goal.
- The unsupported `JEV_MODE` contract claim. Use `--mock`, `--dry-run`, and the
  documented exit codes.

### 📖 Documentation

- A release checklist in `docs/release.md` covering checks, signed tags, the
  public remote, npm publication, and rollback.

### ⚙️ CI

- CI actions are pinned to immutable commits; release packaging checks the
  tarball and the tag/version match.

### 📦 Release

- Published as `libreharness@1.0.0` on npm; the GitHub repository remains
  private.
- Release publishing uses npm OIDC trusted publishing. There is no long-lived
  `NPM_TOKEN`; the first package version was bootstrapped with staged
  publishing.
- The package declares `os: linux`, and release CI runs on Ubuntu.

### ⚠️ Limits

- No 1.0.0 benchmark has been run. No performance claim is made; the restored
  experiment reports are historical.
- Linux and OpenCode only. macOS, Windows, and other host adapters are outside
  the 1.0.0 support scope.

## 1.0.0-rc.1 — 2026-10-30

First local candidate: the queue, workflow, skills, agents, commands, plugins,
and Jev clients in one tree.

### 🚀 Features

- A Markdown work queue in `bin/tasks.py`: tasks, goals, dependencies, lanes,
  ownership checks, atomic writes, a generated board, and a workflow metrics
  log.
- A risk-scaled engineering workflow in `AGENTS.md` and the `engineering-loop`
  skill: intake, gate only what applies, choose one path, prove the claim, and
  close with evidence.
- Five portable skills: `engineering-loop`, `goal`, `parallel-lanes`,
  `ui-design`, and `work-queue`.
- Agents for read-only exploration, bounded implementation, integration, and
  independent challenge.
- Commands for goal intake, briefs, lanes, review, integration, close,
  handoff, harvest, takeover, queue inspection, UI review, and tuning.
- Four local plugins: `auto-intake`, `close-reminder`, `goal-watch`, and
  `security-guard`.
- Jev advisory clients for diff review, goal-plan critique, and close triage.
  The client reads `JEV_MODEL`, `JEV_ENDPOINT`, `JEV_MODELS_URL`, `JEV_API_KEY`,
  and `JEV_KEY_FILE`, and supports `--mock` and `--dry-run` for review and
  plan.
- Unit tests for the queue and Node tests for the bundled plugins and example
  plugins. The tests use temporary state and mocks and do not call a live
  model.

### 🧭 Behaviour

- The queue, plugins, and commands resolve code from `HARNESS_HOME` and
  mutable state from `HARNESS_STATE`.
- The example config is provider-agnostic. It contains no model ID and no key.
  The core does not hardcode a model.
- Jev has no default model. A live call requires `JEV_MODEL`.
- The local plugins never block a session when their configuration is missing.

### 🛡️ Security

- The public tree is sanitized: no private knowledge base, personal tasks,
  hostnames, credentials, or private calibration diffs.
- The Jev client refuses secret-shaped diff or task input unless the caller
  explicitly allows it.
- `auto-intake` refuses secret-shaped prompts and redacts secret-shaped and
  PII-shaped text in task titles.

### 📖 Documentation

- A documentation set covering install, quickstart, concepts, workflow,
  commands, skills, plugins, model routing, skill evaluation, Jev, the adapter
  contract, calibration, security and privacy, troubleshooting, FAQ, and
  design notes.

### ⚠️ Limits

- No benchmark has been run. The repository makes no performance claim.
- Windows is not supported in 1.0.0. The queue uses `fcntl`, so it is POSIX
  only.
- The intended helper set includes scripts that are not all present in this
  candidate: `bin/doctor.py`, `bin/check_spdx.py`, and `bin/scan_private.py`.
  The install guide gives a manual check when a helper is absent.
- The shared Jev module `bin/jev_common.py` is not present. The three clients
  share functions by importing from `bin/jev_review.py`.
- `JEV_MODE` is a documented contract value but is not read by the rc.1
  clients. Use `--mock` and `--dry-run`, and treat a missing key as exit 3.
- `bin/jev_triage.py` has no mock mode.
- `close-reminder` desktop notifications use `notify-send` and are Linux only.
  Other platforms silently fall back to no notification.
- The example plugins contain example model IDs that may rotate or disappear.
- CI workflows are present, but publication CI has not been run or verified.
