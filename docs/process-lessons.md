<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Process lessons

One dated entry per completed task. Keep it short: what surprised us, what it
cost, the rule that changes the next decision, and the doc that now carries it.

Use this format:

```text
## YYYY-MM-DD - short title

Surprise: ...
Cost: ...
Rule: ...
Doc updated: ...
Promote-to-global: yes | no
```

The project ledger starts empty in the public tree. Project-specific and
benchmark-experiment lessons stay in the local brain archive, not here.

## 2026-11-04 - LibreHarness 1.0.0 npm release

Surprise: npm's CLI web-auth URL expires in about 60 seconds, and a phone
passkey returned "Something went wrong" in that flow after staged approval
worked.
Cost: two failed direct-publish attempts and one manual stage/approve.
Rule: bootstrap a new package with `npm stage publish` and approve on
npmjs.com when the account uses a phone passkey; reserve direct `npm publish`
for a desktop authenticator.
Doc updated: `docs/release.md` (staged-first bootstrap), `docs/README.md`
(published status).
Promote-to-global: no

## 2026-11-07 - Default state-machine audit

Surprise: none.
Cost: one command, one skill, one review gate, and one tune pass.
Rule: stateful changes run the `state-audit` skill and update
`docs/state-machines.md` before review; a confirmed invalid transition gets a
regression test before the fix.
Doc updated: `AGENTS.md`, `commands/review.md`, `commands/tune.md`,
`docs/command-reference.md`, `docs/skills.md`, `docs/when-to-use.md`,
`docs/workflow.md`.
Promote-to-global: yes

## 2026-11-07 - OpenCode V2 plugin packaging

Surprise: the V2 server plugin API registers commands, agents, and skills
directly; the copy installer was the source of the drift.
Cost: a package entrypoint, a plugin test, and a clean npm install proof.
Rule: ship harness behavior as a versioned V2 plugin; keep the copy installer
only as an offline fallback.
Doc updated: `docs/install.md`, `README.md`, `CHANGELOG.md`.
Promote-to-global: yes

## 2026-11-07 - AgentEditor has no add; mocks must match the API

Surprise: the V2 `AgentEditor` updates existing agents but has no `add`; the
mocked editor had one, so the test passed while the live plugin was disabled.
Cost: one live failure and a service restart to clear the disabled plugin.
Rule: a mock must mirror the published API, and a clean-config live load is
part of the proof. Agent stubs must be declared in `opencode.json`.
Doc updated: `docs/install.md`, `README.md`, `CHANGELOG.md`.
Promote-to-global: yes

## 2026-11-07 - Config-defined agents are not in editor.get

Surprise: `editor.get` returned undefined for `implementer`, `integrator`, and
`devils-advocate`, but `editor.update(id)` still applied. Gating updates on
`get` left three agents with empty system prompts.
Cost: a live/fresh inventory comparison found it after the first fix.
Rule: update agents by id; never use `get` as an existence gate. Prove all four
prompts and models in both an existing and a fresh config.
Doc updated: `docs/install.md`, `CHANGELOG.md`.
Promote-to-global: yes

## 2026-11-07 - Bundle local plugins after env setup

Surprise: the four local plugins already used the V2 server API; the fresh gap
was packaging, not compatibility. Dynamic imports evaluated their env constants
before setup, so they must load after `HARNESS_HOME`/`HARNESS_STATE` are set.
Cost: one dynamic-import pass and a hook-integration test.
Rule: one plugin entry should own all harness behavior; set env first, then
import feature modules. Do not require a copied `plugins/` directory.
Doc updated: `docs/install.md`, `docs/plugins.md`, `CHANGELOG.md`.
Promote-to-global: yes

## 2026-11-07 - Custom agents need an explicit read rule

Surprise: the build agent's `* allow` did not cover the custom subagents. With
no `read` rule, V2 asked for every subagent read; the external guards only
protected env/secret files.
Cost: every explore/implementer/integrator/devils read prompted until each
agent got `read * allow` plus `.env` ask rules.
Rule: every reading custom agent needs `read * allow`. Keep `.env` policy in
one guard (EnvSitter or one global rule), not repeated per agent. Verify the
live `/api/agent/{id}` permissions, not just the Markdown file.
Doc updated: `agents/*.md`, `docs/plugins.md`, `tests/plugin.test.mjs`.
Promote-to-global: yes

## 2026-11-07 - Default state is a real directory

Surprise: the plugin honoured `HARNESS_STATE`, so the setup could quietly point
at a brain symlink instead of the documented default.
Cost: moving the symlink and seeding the queue once.
Rule: a plugin's user-facing default must not be overridden by the ambient
environment unless the option is documented. Keep state a real mode-700
directory; keep a knowledge base separate.
Doc updated: `docs/install.md`, `README.md`, `CHANGELOG.md`.
Promote-to-global: yes

## 2026-11-08 - A permissive mock hides the argument contract

Surprise: the command test accepted any `session.prompt` argument, so a review
could not tell whether the handler sent a flat `SessionPromptInput` or a nested
`prompt`. The installed V2 types showed the flat shape was correct.
Cost: one type lookup and one extra assertion.
Rule: assert the real argument shape at the boundary; do not let a no-op mock
prove only that the handler ran.
Doc updated: `tests/plugin.test.mjs`, `README.md`, `docs/install.md`.
Promote-to-global: yes

## 2026-11-08 - A skipped publish is an untested publish

Surprise: the 1.0.0 release run was green because npm already had the version;
the workflow skipped `npm publish`, so OIDC trusted publishing was never
exercised. The 1.1.0 tag failed at exactly that step.
Cost: one failed release run and a human trusted-publisher gate.
Rule: treat "already published; skipping" as no proof. Exercise the publish
path with a prerelease, or verify the trusted-publisher configuration before
tagging.
Doc updated: `docs/release.md`, `.github/workflows/release.yml`.
Promote-to-global: yes

## 2026-11-08 - Link checks must exclude installed dependencies

Surprise: adding `@opencode/plugin` made `npm install` create a large
`node_modules` tree; the `**/*.md` lychee glob then reported 81 broken links in
third-party readmes and failed every CI matrix cell.
Cost: one full CI matrix rerun.
Rule: repo-wide link checks exclude `node_modules` (and other vendor/build
directories); check tracked documentation only.
Doc updated: `.github/workflows/ci.yml`.
Promote-to-global: yes
