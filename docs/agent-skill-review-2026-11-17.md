<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Ten agent-skill repositories: fit review

Status: **review complete; no third-party dependency adopted.** This document
records what each repository in the referenced post does, what LibreHarness
could use, and what should stay out. No repository was installed or run.

The post is a list of ten agent skills and tools. Most are aimed at a coding
assistant's output quality, not at a harness's durable state, review, or
recovery loop. The useful material is narrow: one practice to adopt now, two
optional integrations to measure, and a set of ideas to borrow without vendoring
the packages.

LibreHarness already follows the shape of Lauren Tan's pstack: short named
principles, small skills, evidence before a completion claim, and independent
review. The question is therefore not which package to copy. It is which
practice fills a gap in that shape without adding a second methodology.

Sources were read from the public repositories on 2026-11-17 at the pinned
commits below. Star counts are context, not evidence of fit or quality. No
self-reported benchmark number is repeated as a result.

| Repository | Pinned commit | License |
|---|---|---|
| [Ponytail](https://github.com/DietrichGebert/ponytail) | [`96608e0`](https://github.com/DietrichGebert/ponytail/tree/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846) | MIT |
| [Hallmark](https://github.com/Nutlope/hallmark) | [`04977e1`](https://github.com/Nutlope/hallmark/tree/04977e15f3dfd6ee4b74c887dac3eb52665d6c92) | MIT |
| [last30days](https://github.com/mvanhorn/last30days-skill) | [`a854f3b`](https://github.com/mvanhorn/last30days-skill/tree/a854f3bcb2c4344d7498426d653378510f8b253a) | MIT |
| [Humanizer](https://github.com/blader/humanizer) | [`b48c832`](https://github.com/blader/humanizer/tree/b48c832f0f809c1b5658edbb838c2521b72f2413) | MIT |
| [Impeccable](https://github.com/pbakaus/impeccable) | [`d41d986`](https://github.com/pbakaus/impeccable/tree/d41d9860b0094dcb68030657da63461212835aaa) | Apache-2.0 |
| [REA](https://github.com/morluto/rea) | [`e415ba6`](https://github.com/morluto/rea/tree/e415ba6673ca368d5ce2b9e02a8a9b5838ca7f93) | MIT |
| [Graphify](https://github.com/Graphify-Labs/graphify) | [`340268a`](https://github.com/Graphify-Labs/graphify/tree/340268a70a83588d6b3c6de1fffb05326350ef1d) | Apache-2.0 |
| [Taste](https://github.com/senlindesign/taste-skill) | [`6dce223`](https://github.com/senlindesign/taste-skill/tree/6dce223f2f5665d3636ca9a44ec3a7aa1322a9b8) | none |
| [Scrapling](https://github.com/D4Vinci/Scrapling) | [`2998c9e`](https://github.com/D4Vinci/Scrapling/tree/2998c9ebba52ef6116f0a483c7d2f21908250024) | BSD-3-Clause |
| [Diagram Design](https://github.com/cathrynlavery/diagram-design) | [`f6db0de`](https://github.com/cathrynlavery/diagram-design/tree/f6db0decea96de66b901331a0f79a8d4b147ebae) | MIT |

## 1. The filter

LibreHarness is a workflow product, not a general agent toolbox. A repository
has to pass five tests before it joins the core:

1. **Fit.** It must improve durable state, evidence, review proportional to
   risk, recovery, or the autonomy loop. A better UI or a better prose style can
   be useful, but it is not the harness's job.
2. **Cost.** Core behavior is stdlib Python, Node built-ins, and a 120-line
   skill budget. A package that adds a runtime, a service, a database, or a
   large always-on instruction surface has to earn that cost.
3. **Trust boundary.** The harness is local-first with no telemetry and no
   hidden network call. A third-party hook, MCP server, browser engine, or
   install script extends the attack surface and needs a separate review.
4. **License.** MIT, Apache-2.0, and BSD-3-Clause allow adaptation with
   attribution. No license means ideas only, never copied text or code.
5. **Proof.** A benchmark claim follows
   [benchmark-proof.md](benchmark-proof.md). A vendor's self-reported number is
   a hypothesis, not a result.

## 2. Verdicts at a glance

| Repository | What it is | Core cost | Verdict |
|---|---|---|---|
| Ponytail | Minimal-code prompt, review, and audit | Prompt only | **Adopt one practice** |
| Graphify | Local code knowledge graph with query, path, and explain | Python 3.11, tree-sitter, graph artifact | **Pilot as optional** |
| Impeccable | Design vocabulary plus a deterministic slop detector | Node, engine binary, hooks, telemetry | **Optional CLI gate, pin only** |
| Hallmark | Anti-slop design skill with themes and a browser lint | Node plus Chrome for render checks | **Borrow two ideas** |
| Taste | URL to design tokens and rationale | Playwright MCP plus Chromium | **Reject for vendoring; ideas only** |
| Humanizer | Prose de-slop skill with 26 tells | Prompt only, about 500 lines | **Distill, optional docs pass** |
| Diagram Design | Editorial HTML and SVG diagrams | Prompt plus browser for PNG export | **Reject for docs; optional publishing** |
| REA | Reverse-engineering MCP for binaries and apps | Node 22 plus native analysis engines | **Reject for core** |
| Scrapling | Web scraping framework with browsers and proxies | Python, browsers, proxy and captcha layer | **Reject for core** |
| last30days | Social research across Reddit, X, YouTube, and more | Network, API keys, very large skill | **Reject for core** |

## 3. Repository by repository

### Ponytail

One MIT prompt, about 55 lines, that makes the agent take the first option that
fully works: does the thing need to exist, is it already in the repository, does
the standard library or platform do it, is a dependency already installed, can
it be one line, and only then the minimum that works. It also ships review and
audit commands, a `shortcut:` comment convention, and host adapters. The README
claims large code, token, and cost reductions; those are self-reported and were
not reproduced here.

**Genuinely useful.** The pre-change scope check: read the code the change
touches, list every place the change must reach, and include the callers,
tests, fixtures, config, and exports. That is the class of bug a diff-only
review misses: a shared symbol changes, the diff looks clean, and an unchanged
caller breaks. LibreHarness asks for a safety fact and a state-machine impact,
but it does not require this reachability list on a routine diff.

**Why not the package.** The harness already has "Subtract before you add" and
the `unslop` skill. A permanent "lazy senior dev" persona with three intensity
levels, its own board, and host hooks would compete with the operator's voice
and with the existing review protocol. The useful part is one paragraph, not a
second methodology.

**Verdict:** adopt the reachability practice in the brief, the implementer, and
the review. Treat the `shortcut:` marker as an optional second step, not a new
required convention.

### Graphify

A local knowledge graph over code and documentation. Code is parsed with
tree-sitter, so the code map needs no model or API key. It writes `graph.json`,
a report, and an optional visualization, and supports `query`, `path`, and
`explain` over the graph. Every edge is tagged `EXTRACTED` or `INFERRED`, which
is the most useful honesty feature in the repository. It also has an MCP server
and can write instruction-file guidance for OpenCode and other hosts.

**Genuinely useful.** Impact analysis. A review can ask "what connects this
symbol to the route, the schema, and the test" or "what is the shortest path
between these two modules" before reading files one by one. That is a direct
answer to the harness's context-window principle and to the reachability gap.

**Why not the package.** It adds Python 3.11, `uv`, tree-sitter, a new
`graphify-out/` artifact, and an install step that writes agent instructions.
Its documentation semantic pass can use a model or an API key. The "80% fewer
tokens" claim is vendor-reported and was not measured here. None of that is
fatal, but all of it is a new dependency and a new failure mode for a harness
that currently has no third-party Python package.

**Verdict:** optional companion for large repositories. Pilot it on one real
task and measure review findings, tokens, and wall time before any skill tells
an agent to use it. Never make it a package dependency.

### Impeccable

A large design vocabulary for coding agents: 24 commands, a scored critique and
technical audit, and a deterministic detector with 62 rules. The detector is
the interesting part because it runs without a model and returns exit code 2 on
findings. It also ships edit hooks, a live browser mode, a browser extension,
and a catalog request that its README separates from telemetry.

**Genuinely useful.** A deterministic UI gate. `/design-review` is currently an
LLM judgment pass. A pinned `npx impeccable detect` run in CI or before a design
review would give the harness a check that can fail the same way twice, which is
closer to the evidence gate than another opinion.

**Why not the package.** The hooks run outside model approval; live mode can
invoke a CLI with approvals and sandboxing off; and the skill downloads an
engine binary. That is a large trust surface for a harness that promises a
local-first boundary with no hidden network. The 62-rule detector is also
UI-specific, so it does not belong in the default install.

**Verdict:** optional CLI only, pinned version, no hooks and no live mode. Pilot
it on a UI repository and compare its findings with the existing design review.

### Hallmark

An anti-AI-slop design skill with fifty themes, browser-based sloplint checks,
redesign and audit modes, and a fresh-context reviewer. It separates gates into
a floor that never ships, reflex defaults that can be overruled on the record,
and finish checks that never block.

**Genuinely useful.** Two ideas transfer without the package:

- **Preservation check.** A redesign records every link, field, handler, and
  heading first, then fails if one disappeared. The harness's design review
  asks for a visual pass but does not mechanically check that the old wiring
  survived.
- **Tiered gates.** Floor, reflex, and finish is a clean way to say what blocks,
  what needs a recorded exception, and what is advisory. It is the same shape as
  LibreHarness's risk-scaled review.

**Why not the package.** It needs Node and Chrome for the render checks, carries
a large theme and reference tree, and is a UI product rather than a workflow
primitive.

**Verdict:** borrow the preservation check and the tier names into `ui-design`
and `/design-review` when a UI task needs them. Do not vendor the skill.

### Taste

Turns a public URL into a design map and "Taste DNA": four-part trade-offs in a
Trigger, Decision, Reason, Evidence shape, backed by a real browser capture. It
requires the Playwright MCP server and a Chromium download.

**Genuinely useful.** The rationale format. A design rule that states why it
exists and what it rejected is more reviewable than an adjective. The anti-slop
grep is a small deterministic check the harness could copy as an idea.

**Blocker.** The GitHub API reports no license for the repository. Its text and
code cannot be vendored or adapted safely. The Playwright MCP dependency is
also larger than the value for a workflow harness.

**Verdict:** ideas only; no copied text or code. If the operator wants it, it
belongs in the user's global skills, not in LibreHarness.

### Humanizer

A prose-editing skill built from Wikipedia's "Signs of AI writing". It lists 26
patterns, from not-X-but-Y contrasts and one-line closers to chat residue and
re-explaining what the reader already knows, and it is careful to keep every
claim.

**Genuinely useful.** The five strongest structural tells and the claim-
preservation rule. LibreHarness produces a lot of prose: task briefs, review
verdicts, close reports, and public docs. A short checklist could improve them.

**Why not the package.** The skill is about 500 lines, far over the 120-line
budget, and prose quality is not the harness's bottleneck. The project docs are
already plain, and a second full writing methodology would be process weight.

**Verdict:** optional docs pass. If adopted, distill the five tells into a short
checklist and keep the claim-preservation rule; do not vendor the skill.

### Diagram Design

An agent skill for 50 diagram types, rendered as one self-contained HTML file
with inline SVG. It can import Mermaid, draw.io, Excalidraw, and PlantUML, match
a brand from a URL, and export PNG or SVG. The repository itself says Mermaid is
the better fit for docs that live in Git and change every sprint.

**Genuinely useful.** The design principles: one accent, a 4px grid, every node
earns its place, and an import fidelity ledger that says what was merged or
dropped. Those are good editorial rules.

**Why not the package.** The harness's `state-audit` skill requires a Mermaid
statechart in Markdown so it diffs in review. Diagram Design's output is a
generated HTML file with no text source to diff. Adopting it for the state
document would weaken the evidence and review path. It also loads Google Fonts
by default and needs a browser for PNG export.

**Verdict:** reject for the state-audit and docs path. It can be a user-level
publishing tool for a one-off public diagram.

### REA

A reverse-engineering MCP server that inspects native binaries, JavaScript and
Electron apps, .NET assemblies, Android packages, firmware, and websites, with
evidence and stated limitations. It needs Node 22 and can use Hopper, Ghidra,
IDA, or other native engines.

**Genuinely useful.** The evidence-and-limitations discipline is good, and the
tool is strong for a specific investigation of a third-party app. That is not
the harness's job.

**Why not the package.** It is a different product with a large tool catalog, a
large context cost, native-engine dependencies, and runtime capture that runs
targets with the user's permissions. None of that improves the queue, the review
protocol, or the autonomy loop, and it expands the security surface.

**Verdict:** reject for core. A user who needs reverse engineering can install it
outside the harness.

### Scrapling

A Python scraping framework with HTTP fetchers, stealth browsers, JavaScript
rendering, session and proxy rotation, Cloudflare handling, spiders, and an MCP
server and agent skill.

**Genuinely useful.** Clean Markdown extraction and a crawler with pause and
resume are solid engineering. The harness does not need them: `webfetch` covers
normal documentation reads, and a crawler is not part of the queue or review
loop.

**Why not the package.** It adds a large Python dependency, browsers, proxy and
captcha handling, and network behavior that conflicts with the local-first
boundary. The repository's own disclaimer puts the compliance burden on the
user.

**Verdict:** reject for core.

### last30days

A research skill that pulls recent posts and engagement from Reddit, X, YouTube,
TikTok, Instagram, Hacker News, Polymarket, GitHub, and the web, then synthesizes
a summary. Its skill file is about 78 KB and over a thousand lines, and many
sources need network access or API keys.

**Genuinely useful.** It is a capable topic-research tool. That is useful for a
market or ecosystem question, not for a durable work queue.

**Why not the package.** The context cost alone exceeds the harness's skill
budget many times over, and the data is ephemeral. It adds network and API-key
handling without improving state, evidence, review, or recovery.

**Verdict:** reject for core. Optional user-level tool for research.

## 4. Fit against the harness goals

Qualitative, not measured. `+` means it helps, `0` means neutral, `-` means it
adds cost or risk.

| Repository | Autonomy | Continuity | Self-improvement | Security | Reliability |
|---|---|---|---|---|---|
| Ponytail | 0 | 0 | + | 0 | + |
| Graphify | + | 0 | + | - | + |
| Impeccable | 0 | 0 | 0 | - | + on UI only |
| Hallmark | 0 | 0 | 0 | - | + on UI only |
| Taste | 0 | 0 | 0 | - | 0 |
| Humanizer | 0 | 0 | 0 | 0 | 0 |
| Diagram Design | 0 | 0 | 0 | - | - for docs |
| REA | 0 | 0 | 0 | - | 0 |
| Scrapling | 0 | 0 | 0 | - | 0 |
| last30days | 0 | 0 | 0 | - | 0 |

The pattern is clear: almost nothing in the list improves autonomy or
continuity, which are the harness's differentiators. The strongest candidates
improve reliability of a specific step, not the loop itself.

## 5. Recommendation

### Adopt now, with no new dependency

Add a **reachability check** to the existing loop. It is one practice, not a
package:

1. In `commands/brief.md`, add a **Reach** line to the one-page brief: the
   callers, importers, tests, fixtures, config, and exports the change must
   reach.
2. In `agents/implementer.md`, make the pre-edit inspection enumerate the same
   list. If the list cannot be produced, report the uncertainty instead of
   editing.
3. In `commands/review.md`, before the verdict, read the unchanged callers of
   every changed shared symbol. A diff that renames or changes a shared symbol
   without that check is incomplete.

Why this one: it needs no install, no network, and no new file format. It
targets a real failure class that a diff-only review misses. It also gives the
review a concrete question instead of a general "state impact" instruction.

Measure it before calling it a win: take one seeded rename or signature change
with an unaffected caller, and show the current review misses it while the new
step catches it. Record the review tokens and wall time beside the result.

### Pilot, but keep optional

- **Graphify** on a large repository. Predeclare the metrics: findings outside
  the diff, false leads, tokens, and wall time. Keep `graphify-out/` out of the
  repository and the package. Adopt only if it finds more than the current
  explore path at an acceptable cost.
- **Impeccable's detector** on one UI repository, pinned and CLI-only. Compare
  its findings with `/design-review`. Do not install its hooks, live mode, or
  extension in the default harness.

### Borrow ideas, not packages

- **Hallmark:** the redesign preservation check and the floor, reflex, finish
  tiers.
- **Taste:** the Trigger, Decision, Reason, Evidence format; no copied text,
  because the repository has no license.
- **Humanizer:** the five strongest prose tells and the claim-preservation rule,
  distilled into a short checklist if docs quality becomes a real problem.

### Reject for the core

REA, Scrapling, last30days, and Diagram Design are useful tools for their own
jobs, but none improves the queue, the review loop, the evidence gate, or the
autonomy path. Adding any of them would grow the dependency and security surface
without moving the harness's own metrics.

## 6. What was not verified

- No repository was installed or run against OpenCode. OpenCode support is
  taken from each README, not from a live test.
- No benchmark was reproduced. Ponytail's and Graphify's performance claims are
  vendor-reported and are not used as evidence here.
- The licenses were read from the GitHub API on 2026-11-17. Taste has no
  license file at that commit, so its text and code are not reusable. Star
  counts were read for context but are not used as a fit signal.
- Impeccable's hooks, live mode, and network behavior were read from its README,
  not audited in a sandbox.
- The reachability practice is a reasoned response to a gap. It has not been
  measured yet; the proposed seeded-rename check is the first proof.
- No claim is made that any of these tools improves coding quality on
  Terminal-Bench or on the review fixtures.

## 7. Next

1. One task for the reachability practice in the brief, implementer, and review,
   with a seeded-rename check as evidence.
2. One optional Graphify pilot with the metrics above, kept outside the package.
3. One optional Impeccable detector pilot on a UI repository, CLI only.
4. No third-party dependency enters the default package until a pilot passes
   the predeclared rule.
