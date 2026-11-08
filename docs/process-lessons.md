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
