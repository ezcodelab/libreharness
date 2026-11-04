<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Google EGM review and benchmark integration strategy

Status: **review complete, adoption not approved.** This document records what
the Elephant-Goldfish Model (EGM) does, what LibreHarness should take from it,
and whether the custom Harbor adapter is still the right benchmark integration.

Source: [`google/elephant-goldfish-model`](https://github.com/google/elephant-goldfish-model)
at commit [`403d8881d62022490637d740657b33f01e321ea8`](https://github.com/google/elephant-goldfish-model/tree/403d8881d62022490637d740657b33f01e321ea8),
Apache-2.0, last source change 2026-10-30. The repository had 7,298 stars and
442 forks when checked on 2026-10-31. It is a prompt and skill package, not an
ML model. No prompt blocks are copied here.

## 1. What EGM actually is

EGM is a spec-driven development method packaged as seven skills, seven
reviewer personas plus a synthesizer, and five document standards:

- **Elephant.** A long-running, context-rich session that interviews the
  engineer, explores trade-offs, and writes a design document. It does not write
  production code.
- **Goldfish.** Fresh, zero-context subagents that read only the document and
  the files it references. They test comprehension, attack the design, and
  check implementation readiness.
- **Human.** Chooses the architecture, resolves findings, and approves the
  document before implementation.

The lifecycle is:

```text
brainstorm -> draft -> review -> resolve -> human approval -> implement -> drift report
```

The review pipeline has five stages: zoom-out, comprehension, critic,
intermediate zoom-out, and implementation readiness. A review loop adds
settled-findings tracking, a two-clean-round convergence rule, a five-round cap,
and a churn check. A reviewer that fails is recorded as `not run`, never as a
reviewer with zero findings.

The source is mostly Markdown instructions. The executable part is a small
Python test suite that checks manifests, links, frontmatter, skill size, and
Claude/Codex isolation. I ran that unit suite against the pinned commit: it
passes. It does not measure review quality.

## 2. Pros

1. **The comprehension test is a real serialization test.** A fresh reader must
   paraphrase the document and explain how the existing system works. If it
   cannot, the document depends on conversation memory that never reached the
   file. This is cheap and catches a failure that ordinary diff review misses.
2. **Fresh context removes anchoring.** The reviewer did not sit through the
   design debate, so it cannot inherit the author's blind spots. The method
   states this explicitly and refuses to run when the host cannot create a
   fresh context.
3. **The design artifact is durable.** The spec is checked in, linked from the
   pull request, and readable by the next session, teammate, or model. It is a
   better handoff than a chat transcript.
4. **The personas make critique specific.** “Naive reader”, “skeptical
   architect”, “implementation readiness”, and “codebase auditor” each have a
   different failure mode to look for. The standards give them a common bar.
5. **The convergence rules are better than “review until it feels done.”**
   Settled findings stay settled, a fixed finding re-opens if it returns, two
   clean rounds are required, and the loop caps at five rounds. A failed
   reviewer is not counted as a clean reviewer.
6. **Human ownership is explicit.** The method forbids autonomous pull
   requests, auto-accept is a user choice, and the human resolves trade-offs.
   The review is evidence, not a gate controlled by a model.
7. **The packaging is honest about limits.** The harness table distinguishes
   tested paths from cloud gaps, records fixture runs, and says a review does
   not replace tests or human judgment.
8. **The tests catch packaging drift.** Manifest metadata, skill size, links,
   frontmatter, and reviewer isolation have offline checks. The skill body limit
   forces details into referenced files instead of one giant prompt.

## 3. Cons and risks

1. **The token multiplier is large and unbounded by task size.** A full review
   can run nine or more reviewer calls per round, with optional duplicate
   reviewers, and up to five rounds. There is no token budget in the skill; the
   only cap is the round count.
2. **Fresh context is enforced by prompt, not by the runtime.** The host must
   provide a real subagent with isolated context. If the host leaks the parent
   transcript, the method still appears to work while losing its main
   advantage. The repository tests this for Claude and Codex, not for every
   host.
3. **Zero-context reviewers invent requirements.** A reviewer that cannot see
   an unwritten team convention may call it a blocker. The resolution step
   pushes the judgment back to the author, and “auto accept” can apply a
   plausible but wrong fix.
4. **The rubrics are qualitative.** Severity, “clean round”, and “implementation
   readiness” are model judgments. The method reduces self-review bias but does
   not produce a deterministic score.
5. **Drift detection is manual.** The design document is checked in, but the
   drift report is a weekly or ad-hoc skill. Nothing in CI fails when the code
   and the spec diverge.
6. **Documentation can become the bottleneck.** EGM's own FAQ says design review
   adds work and can overload reviewers. The method is explicitly not for every
   small change, but the skills do not enforce that boundary.
7. **The standards can force false precision.** “Zero design decisions left to
   the implementer” is a useful ideal, but it can produce a brittle plan that
   specifies details the author cannot know yet. The implementation-readiness
   reviewer may reward over-specification.
8. **The method is harness-shaped.** Skills name host-specific subagent tools
   and plugin paths. Portability is tested, but not universal; OpenCode is not
   in EGM's supported harness table.
9. **The public evidence is adoption, not efficacy.** “Thousands of Google
   engineers” and 7,298 stars show use and interest. They do not show a measured
   quality gain over a plain coding agent. The repository's own test record is
   fixture-level and often partial.
10. **The review swarm can flatten disagreement.** The synthesizer deduplicates
    findings and writes one report. That is good for noise, but it can hide the
    fact that two reviewers disagreed about whether something is a blocker.

## 4. Fit with LibreHarness

LibreHarness already has a queue, goals, lanes, a design gate for one-way doors,
an independent `devils-advocate`, Jev's typed review, and an evidence gate. EGM
should not replace that. The useful overlap is narrow:

| EGM feature | LibreHarness today | Gap | Token note | Decision |
|---|---|---|---|---|
| Elephant / spec-first design | Task `Plan`, design notes, one-way-door memo | No standard spec artifact for every multi-file change | One spec read; no extra reviewer | **ADOPT-LITE**: use the task `Plan` as the spec; add a comprehension check, not a new document tree |
| Zero-context comprehension test | `devils-advocate` is a fresh subagent, but it reviews a supplied packet, not a read-back | No explicit “explain it back” gate | +15k to +25k input per call | **ADOPT**: one fresh reader, one call, before implementation on nontrivial specs |
| Implementation-readiness review | Design gate asks for alternatives and reversibility; task acceptance is testable | No checklist for file paths, interfaces, migrations, rollback | +15k to +25k input per call | **ADOPT-LITE**: add the checklist to the design gate for multi-file or one-way changes |
| Settled / fixed / clean-round / cap / churn rules | Review send-backs and Jev verdicts, but no convergence ledger | Reviews can loop or re-litigate settled findings | Adds rounds; capped at five | **ADOPT**: add the rules to the review protocol |
| Failed reviewer = `not run` | Review says a missing reviewer is a warning | Not explicit in the protocol | No extra tokens; prevents a false clean round | **ADOPT**: one line and one test |
| Multi-persona Goldfish swarm | One `devils-advocate`; Jev axes | No design-critic / YAGNI / style swarm | Three reviewers per stage; roughly 2x to 3x review tokens | **DEFER**: measure the single comprehension check first |
| Drift report | No checked-in specs, no CI drift gate | Specs would rot | Reads every spec and referenced code; weekly, not per task | **DEFER**: build only after specs exist |
| Bootstrap README hierarchy | Docs already have an index and per-area pages | Duplicate documentation | One pass per directory; large one-off cost | **DEFER**: not worth the duplication while the docs are current |
| Six-lens brainstorm swarm | Goal/plan plus `devils-advocate` | Heavy upstream ideation | Six reviewers per brainstorm | **DEFER**: not the current bottleneck |
| Interactive auto-accept resolution | Human review and task evidence gate | None; auto-accept would weaken it | No extra tokens; raises wrong-fix risk | **REJECT**: keep human approval |
| Full EGM plugin | Queue, skills, commands, review protocol | Duplicates ownership and workflow | Duplicates context and skill loading | **REJECT**: borrow ideas, not the package |

The smallest useful adoption is: **comprehension check + readiness checklist +
convergence rules + failed-reviewer accounting.** That is three prompt/protocol
changes and one test, not a new subsystem.

## 5. Is the custom Harbor adapter still ideal?

**Yes as the integration mechanism, no as a product.** Harbor documents custom
agents through `-a module.path:ClassName`, including custom harnesses:
<https://docs.harborframework.com/agents/custom-agents>. The adapter is the
supported extension point, not a fork of Harbor.

What stock Harbor 0.25.0 already provides for OpenCode:

- installs and runs the OpenCode CLI;
- uploads a skills directory (`skills_dir`);
- writes an `opencode_config` overlay for providers, models, MCP, and
  permissions;
- parses the JSON stream into an ATIF trajectory;
- reports tokens and cost.

What it does not provide:

- upload of `agents/`, `commands/`, `bin/tasks.py`, or `AGENTS.md`;
- an Ollama Cloud credential destination; its candidate list starts with
  `OPENAI_API_KEY`;
- a clean exit when OpenCode emits EPIPE after a completed answer; its `run()`
  still pipes stdout through `tee`.

The current adapter adds those three things. That is the right scope. The
problem is how it adds them: it copies the whole stock `run()` method. Harbor's
main branch already adds options that the copy does not know about, so the copy
will drift.

**Long-term ideal:** keep the stock `run()` and rewrite only the final command
through the `exec_as_agent` extension point. The rewrite would:

1. replace the `| stdbuf -oL tee <log>` tail with a direct write to the same
   log;
2. capture the exit code;
3. tolerate a non-zero exit only when the combined captured stream shows a
   completed `step_finish` with `reason: "stop"` and contains `EPIPE`; the
   observed EPIPE trace is at the head of the log, not the tail;
4. otherwise raise through Harbor's `_classify_exec_error` (or
   `NonZeroAgentExitCodeError`) so the trial is recorded as a failure.

That leaves model selection, trajectory parsing, new flags, and error events in
Harbor's hands. A source-contract test should fail when the stock `tee` pattern
changes, so the rewrite cannot silently stop applying. Upstreaming the two
fixes (Ollama key candidate and no-`tee` output) is worth one PR, but the
benchmark should not block on it.

Do not spin the adapter out as a product. The benchmark category already has
early tools:

| Tool | Stars | License | What it does | Maturity |
|---|---:|---|---|---|
| [Harbor custom agents](https://docs.harborframework.com/agents/custom-agents) | official | Apache-2.0 | Runs a custom agent/harness in Harbor | Mature integration point |
| [`ashishpatel26/harness-eval`](https://github.com/ashishpatel26/harness-eval) | 3 | none | Baseline vs candidate harness, CI-style verdicts | Early, unlicensed |
| [`cipherfoxie/agent-bench`](https://github.com/cipherfoxie/agent-bench) | 2 | MIT | OpenCode A/B for skills and MCP | Early |
| [`fy-06/agents-md-bench`](https://github.com/fy-06/agents-md-bench) | 0 | MIT | `AGENTS.md` with/without ablation | Early |
| [`chesterxgchen/agent-skills-bench`](https://github.com/chesterxgchen/agent-skills-bench) | 1 | Apache-2.0 | Skills A/B in Docker | Early |

The gap is not “no one benchmarks harnesses.” The gap is a mature, standardized
way to package a full harness overlay and compare it before and after a change.
That is a LibreHarness feature, not a separate company. Revisit productization
only after a published result and external demand.

## 6. Quality versus token estimate

These are **priors, not measurements.** The pilot data gives the price shape,
not a quality effect. At the pilot-implied Ollama Flash rates (roughly
$0.014 per million input tokens and $0.28 per million output tokens), a full
EGM review is inexpensive in dollars but can be large relative to a small task.

Assumptions for the table:

- one reviewer call reads a 3k-token spec, 10k tokens of referenced files, and
  2k tokens of persona/standard, and writes 1k tokens;
- one synthesizer call reads the findings and spec, and writes 1k tokens;
- a full five-stage review runs about nine reviewer calls and two rounds;
- a large coding task is the pilot's gpt2 size (about 4.9M input, 80k output);
- a small task is the pilot's break-filter size (about 49k input, 2.8k output).

| Arm | Review tokens | Review cost (Flash) | Expected quality delta | Confidence |
|---|---:|---:|---|---|
| Current LibreHarness review | not measured | not measured | baseline | — |
| + comprehension check | +15k to +25k | +$0.001 | 0 to +5 pp; more on ambiguous multi-file work | Low |
| + readiness checklist | +15k to +25k | +$0.001 | 0 to +4 pp; catches missing files and interfaces | Low |
| Full EGM, two rounds | +100k to +300k | +$0.004 to +$0.013 | +3 to +10 pp on design-heavy work; near zero on small clear tasks | Very low |
| Full EGM with duplicate reviewers | +200k to +600k | +$0.008 to +$0.026 | +1 to +3 pp over the full arm | Very low |

The same review is about 2% to 6% of a large task's input tokens and 200% to
600% of a small task's input tokens. That is the real trade-off: the method is
cheap on large work and expensive on small work. Use it where a wrong design
costs more than the review.

Break-even is easier to reason about in rework than in tokens. Twenty reviews
at $0.005 each cost about $0.10; if one prevented failure costs more than that
in model time and human rework, the review pays. For a $0.003 task, the review
can cost more than the task. The method pays only when it catches a design
error early, not because review tokens are cheap.

The fast experiment that replaces these priors is a seeded-defect spec:

- **Baseline:** current LibreHarness review path.
- **Candidate:** add one zero-context comprehension reviewer and the readiness
  checklist.
- **Fixture:** one design spec with five seeded defects (undefined term, wrong
  API signature, missing rollback, missing invariant, untested edge case).
- **Metric:** recall of seeded blockers, false blockers per review, input and
  output tokens, wall time, and cost.
- **Stop rule:** adopt only if the candidate finds at least one more seeded
  blocker at no more than twice the review tokens and no more than one false
  blocker per review.

That experiment runs in minutes on one fixture and does not need Docker or a
coding task. It is the right first measurement; the Harbor/Terminal-Bench result
remains the public headline.

## 7. Recommendation

Adopt now:

1. a one-call, zero-context comprehension check for nontrivial specs;
2. the implementation-readiness checklist in the design gate;
3. settled/fixed/clean-round/cap/churn rules and failed-reviewer accounting in
   the review protocol.

Defer:

- multi-persona swarm, drift report, bootstrap, and six-lens brainstorm until
  the comprehension check shows a measured gain.

Reject:

- the full EGM plugin, auto-accept resolution, and a mandatory design document
  for every change.

Keep the custom Harbor adapter, but make it a thin command-rewrite layer over
stock `OpenCode.run()`, pin Harbor 0.25.0 and OpenCode 1.19.5, and add the
source-contract test. The adapter is benchmark glue; the durable product is the
harness overlay and the reproducible comparison, not the adapter itself.

## 8. What was not verified

- No live EGM review was run on OpenCode. EGM does not list OpenCode as a
  supported harness.
- No controlled quality measurement exists for EGM or for this proposal. The
  table above is an estimate with named assumptions.
- The EGM unit suite passes at the pinned commit, but it tests packaging,
  links, frontmatter, skill size, and host isolation, not review quality.
- The Harbor comparison is from Harbor 0.25.0 source and our live adapter
  trials. Stock Harbor was not run with the full overlay.
- Star counts and licenses were read from the GitHub API on 2026-10-31. They
  are not an endorsement or a maturity guarantee.
