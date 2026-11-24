<!-- SPDX-License-Identifier: MIT -->
# Agent tooling review: three repos

Reviewed 2026-11-24 against OpenCode 2.x with LibreHarness loaded as a plugin
(`gh` CLI for GitHub PRs, Gitea canonical for `brain`, `aequitas`, and
`homelab-*`). The question: does any of this belong in the OpenCode config, in
the LibreHarness repo, or nowhere?

## Verdict

| Repo | License | Runtime cost | Fit | Verdict | Take |
|---|---|---|---|---|---|
| [github/github-mcp-server](https://github.com/github/github-mcp-server) | MIT | Go binary, Docker, or hosted HTTPS | OpenCode tool adapter | Narrow adopt in OpenCode | Read-only `pull_requests` + `actions`; CI failure classes |
| [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | None, Markdown only | LibreHarness skill layer | Skip install, adapt three references | Writing standard, two-axis review, wizard |
| [github/spec-kit](https://github.com/github/spec-kit) | MIT | Python 3.11+, `uv`, per-project files | Competing process engine | Skip adoption | Spec shape, converge pass |

Only the first is a runtime to install. Only the second is cheap to adapt. The
third duplicates what LibreHarness already owns.

## The fit test

LibreHarness already owns four things: intake and task state, the review
artifact, the PR gate, and the skill map (`skills/README.md`). A candidate earns
a place only if it adds a capability without becoming a second owner of those.

1. **One process owner.** Two workflows that both define "task", "review", and
   "done" will disagree, and the agent will follow whichever it read last.
2. **Dependency budget.** `package.json` declares a Node engine and a Python
   3.10 floor; the shipped code is standard library and Node built-ins. A new
   runtime is an operator decision, not a skill install.
3. **Context budget.** Every skill description and every MCP tool schema is
   loaded every turn. The repo caps a `SKILL.md` at 115 lines
   (`tests/harness-ratchets.test.mjs:22`), which is a proxy for the same
   pressure.
4. **Secret and write surface.** Anything that authenticates to GitHub adds a
   token to protect and write tools to gate.

## github/github-mcp-server

**What it is.** GitHub's official MCP server. The local build is Go; the hosted
endpoint is `https://api.githubcopilot.com/mcp/`. It exposes 23 toolsets plus a
bundled skill catalog, and supports `--read-only`, `--toolsets`, and `--tools`
filtering (`README.md`, `docs/installation-guides/install-opencode.md`).

**Fit.** It is a tool adapter, so the install target is
`~/.config/opencode/opencode.json`, never the LibreHarness repo. LibreHarness
does not need to know it exists; `bin/pr_guard.py` and the `shipping` skill keep
using `gh` as the gate.

**Why only narrow.** Three measured limits:

- The default toolset is already five groups (`context`, `repos`, `issues`,
  `pull_requests`, `users`), and the vendor's own OpenCode guide warns that the
  server "can add a lot of tokens to your context" and recommends limiting
  toolsets.
- It cannot serve the Gitea-canonical repos at all. Half this workspace gets
  zero value from it.
- Its 18 bundled skills overlap `pull-request-authoring`,
  `pull-request-code-review`, `release-preparation`, and
  `workflow-failure-triage`. Enabling them would put a second copy of that
  process beside `shipping`, which the fit test rejects.

The genuine gain is structured reads that `gh` makes you parse by hand:
line-anchored review threads, failed job logs in one call
(`get_job_logs` with `failed_only`), security alerts, and notifications.

**Smallest useful install.** Remote server, PAT, two toolsets, read-only
enforced:

```jsonc
"mcp": {
  "servers": {
    "github": {
      "type": "remote",
      "url": "https://api.githubcopilot.com/mcp/",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:GITHUB_PERSONAL_ACCESS_TOKEN}",
        "X-MCP-Toolsets": "context,pull_requests,actions",
        "X-MCP-Readonly": "true"
      }
    }
  }
}
```

Measure the tool count with `opencode mcp list` before keeping it. If the
schemas crowd the window, disable `github_*` globally and enable it only for a
review session, the pattern the vendor documents.

**Take even without installing.** The
`pkg/skills/catalog/skills/workflow-failure-triage/SKILL.md` decision model is
tool-agnostic and applies to Gitea too: classify a red build as code,
infrastructure, configuration, cancelled, or still running; rerun only
`failed_jobs`; never rerun the same run twice without a change. That belongs in
a `shipping` reference, written against `gh run view --log-failed` rather than
MCP tool names.

## mattpocock/skills

**What it is.** 27 Markdown skills (20 engineering, 7 productivity) with a
user-invoked versus model-invoked split, a router (`ask-matt`), and a one-time
`/setup-matt-pocock-skills` that asks which issue tracker to use. MIT, no
runtime. The README explicitly rejects process-owning approaches (GSD, BMAD,
Spec-Kit) and argues for small composable skills.

**Fit.** This is the closest match to LibreHarness's skill layer and the
cheapest to adapt. The length worry is unfounded: `code-review` is 89 lines,
`to-tickets` 105, and `writing-for-agents` 81, all under the 115-line cap. The
blockers are ownership and style, not size.

**Why not install wholesale.**

- It adds 27 always-loaded descriptions and a second router beside
  `engineering-loop`. The skill map doubles.
- Its process assumes the issue tracker is the system of record: `to-spec`
  publishes a spec, `to-tickets` writes tickets, `implement` closes them. In
  LibreHarness the task file is the record, and `/goal`, `plan`, and lanes
  already cover that ground.
- Several skills collide directly: `grill-me` blocks on the human, `handoff`
  duplicates `/handoff`, `implement-spec` duplicates lanes plus the integrator,
  `tdd` overlaps the bug-fix loop.
- The prose is non-ASCII (em dashes, arrows) and would fail the ASCII ratchet
  before it ran.

**Three worth adapting.**

1. **`writing-for-agents` (81 lines).** The best single artifact in the three
   repos. It names the budget the ratchet encodes: context load versus cognitive
   load, context pointers, progressive disclosure, leading words, no-ops,
   sediment. Put an ASCII, trimmed copy at
   `skills/correct/references/skill-writing.md` and link it from `correct` and
   `tune`, so the next skill or `AGENTS.md` edit has a written standard.
   *Check:* `node tests/harness-ratchets.test.mjs` stays green and no new
   always-on line enters `AGENTS.md`.
2. **Two-axis review (89 lines).** Standards (repo rules plus the Fowler smell
   baseline) and Spec (does the diff implement the originating request?) are
   reviewed separately, because a change can pass one and fail the other. Keep
   LibreHarness's default: the review artifact is still deterministic and the
   axes are for an operator-requested second opinion, not an automatic subagent
   fan-out. Put the axes and the smell list at
   `skills/shipping/references/review-axes.md`.
   *Check:* `python3 -m unittest tests.test_tasks -v`; `/review` still makes no
   model call by default.
3. **`wizard` (44 lines), optional.** It fills a real gap: LibreHarness stops at
   a one-way door but only says stop. A wizard script hands the human the exact
   dashboard path, captures values, writes `.env` and `gh secret`, and confirms
   before an irreversible step. Adapt it to route secret writes through
   envsitter, keep the shared bash library untouched, and verify with `bash -n`
   plus `shellcheck`.
   *Check:* a dry run against a throwaway repo captures every value and `bash
   -n` passes.

**Skip.** `grill-me`, `handoff`, `to-spec`, `to-tickets`, `implement`,
`implement-spec`, `tdd`, `triage`, and `research`. Each duplicates an existing
command or playbook, or blocks on the human in a way the queue contract
forbids.

## github/spec-kit

**What it is.** A Python CLI (`specify`) installed with `uv`, nine SDD commands,
templates, and extension, preset, workflow, bundle, and catalog layers. It
writes `.specify/` and generated command or skill files into each project. The
SDD flow is constitution, specify, plan, tasks, implement, converge; the bundled
bug and assess extensions add their own verdicts.

**Fit.** This is a competing process engine, not a library. Adoption would
create a second task model (`T001` phases beside queue tasks), a second verdict
(`verified` / `partial` / `failed` beside the review artifact PASS), a second
state directory (`.specify/` beside `HARNESS_STATE`), and a second command
namespace. It also raises the Python floor from 3.10 to 3.11 and adds `uv` and
per-project generated files that drift from the plugin.

The strengths are in the artifacts, and those survive without the CLI.

**Two worth taking.**

1. **Spec shape.** `templates/spec-template.md` (131 lines) is a better
   large-feature brief than a flat acceptance checklist: prioritized user
   stories that are each independently testable and shippable, an
   `Independent Test` per story, Given/When/Then acceptance scenarios,
   `NEEDS CLARIFICATION` markers instead of invented requirements, measurable
   and technology-agnostic success criteria, key entities, and assumptions.
   Trim it to a reference used by `/brief` when a goal has two to six children;
   a single task keeps the flat checklist.
   *Check:* one real goal brief carries a story, its independent test, and its
   scenarios without adding a second document to the repo.
2. **Converge pass.** `templates/commands/converge.md` (279 lines) has one idea
   worth five lines: re-read the spec, plan, and acceptance against the current
   code, append unmet work as new tasks, never rewrite history, leave the plan
   byte-for-byte unchanged when everything is met, and treat completion claims
   as unevidenced. Add that pass to `/close` or the goal skill.
   *Check:* a close with an unmet acceptance item creates a follow-up task
   instead of recording `done`.

**Skip.** The constitution (AGENTS.md already holds project rules), the bug and
assess extensions (playbooks and the queue cover them), and the catalog,
bundle, and preset layers (no second project to share them with).

## Cross-cutting notes

- **Context is the real bill.** A conservative estimate is 30 to 60 tokens per
  skill description, so the 27-skill install costs roughly 1k to 1.6k tokens
  every turn. The GitHub MCP default schemas are larger, likely several
  thousand. Both are inferred from file and table counts, not measured with a
  tokenizer.
- **Forge split matters.** The MCP only helps the two GitHub-canonical repos.
  A CI failure reference and the two spec shapes help every repo.
- **Do not mix process owners.** The strongest argument against both spec-kit
  and a wholesale skills install is the same: LibreHarness is the process, and
  these are techniques or tools.

## Ranked next steps

| Order | Change | Dependency | Check |
|---|---|---|---|
| 1 | Add CI failure classes to `shipping` | None | `node tests/harness-ratchets.test.mjs` |
| 2 | Add the skill-writing reference to `correct` | None | Same ratchet plus `npm test` |
| 3 | Add the converge pass to `/close` | None | `python3 -m unittest tests.test_tasks -v` |
| 4 | Add the spec shape for goal briefs | None | One real goal brief |
| 5 | Install the GitHub MCP read-only in OpenCode | PAT or OAuth | `opencode mcp list`, then one review-thread read |
| 6 | Add `/wizard` for human-only steps | Bash template | `bash -n` and `shellcheck` |

Steps 1 to 4 are repo-local, reversible, and need no new dependency. Step 5 is
configuration only. Step 6 is the only one that adds a secret-handling surface,
so it goes last.

## Method and limits

Read on 2026-11-24: each repo's `README.md`, the GitHub MCP OpenCode install
guide and its workflow-failure skill, mattpocock's `SCOPE.md`,
`writing-for-agents`, `code-review`, and `wizard`, and spec-kit's `spec`,
`tasks`, and `converge` artifacts. Line counts came from `wc -l` on the raw
files. No server was installed, no config was changed, and no external code was
copied. Token estimates are inferred, not measured.
