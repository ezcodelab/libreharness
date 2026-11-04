<!-- SPDX-License-Identifier: MIT -->

# Changelog

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
