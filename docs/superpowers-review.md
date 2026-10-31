<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Superpowers review and comparison design

Status: **review complete, profiles not implemented.** This document decides
what to borrow from Superpowers, how it compares with EGM and the current
LibreHarness, and what the four-arm evaluation must prove.

Sources:

- [`obra/superpowers`](https://github.com/obra/superpowers) at commit
  [`2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`](https://github.com/obra/superpowers/tree/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b),
  release v7.0.1, MIT, 309,923 stars and 27,569 forks on 2026-10-31.
- [`prime-radiant-inc/superpowers-evals`](https://github.com/prime-radiant-inc/superpowers-evals),
  the Quorum behavioral eval lab, 142 stars, no license at review time.
- [`google/elephant-goldfish-model`](https://github.com/google/elephant-goldfish-model)
  at commit `403d888`, reviewed in [`egm-review.md`](egm-review.md).

No skill body is copied here. The profile implementation is a separate task.

## 1. What Superpowers is

Superpowers is a complete software-development methodology for coding agents.
It ships 15 composable skills and a bootstrap that makes the agent invoke the
relevant skill before acting. The core loop is:

```text
using-superpowers -> brainstorming -> using-git-worktrees
                  -> writing-plans
                  -> LibreHarness queue/lane execution
                  -> test-driven-development -> systematic-debugging
                  -> requesting-code-review -> receiving-code-review
                  -> verification-before-completion
                  -> LibreHarness close/integrate
```

This is an ideal sequence, not a prescription. Superpowers itself says the
skills are fluid and should be reached for when they serve the immediate
bottleneck. The profile keeps LibreHarness's queue and lane execution between
the plan and the verification steps.

Unlike EGM, Superpowers is not only a design-review method. It covers the whole
lifecycle: intent discovery, design, planning, implementation, review,
debugging, verification, and branch completion. It is therefore closer to
LibreHarness in scope and more likely to overlap with it.

The bootstrap is explicit about enforcement: if a skill might apply, the agent
must invoke it before responding. User instructions still take precedence, but
the default is strong process compliance rather than optional advice.

## 2. Skill inventory

| Skill | What it does | Fit for LibreHarness |
|---|---|---|
| `using-superpowers` | Bootstrap; forces skill discovery and invocation | **Adopt in profile**: needed for the other skills to trigger |
| `brainstorming` | Questions the human before building; explores approaches and writes a design | **Adopt in profile, text only**: exclude its executable visual-companion scripts and network path |
| `writing-plans` | Exact files, interfaces, tests, and bite-sized steps | **Adopt in profile**: stronger than the current task `Plan` |
| `executing-plans` | Inline execution with TDD, ledger, and one final review | **Defer**: it calls `subagent-driven-development` scripts and duplicates LibreHarness execution ownership |
| `subagent-driven-development` | Fresh implementer and reviewer per task, plus final review | **Defer**: overlaps LibreHarness lanes and is expensive |
| `test-driven-development` | Red-green-refactor; no production code before a failing test | **Adopt in profile**: concrete per-task gate |
| `systematic-debugging` | Root cause before fixes; no symptom patches | **Adopt in profile**: strong bug-fix discipline |
| `verification-before-completion` | Fresh command output before any success claim | **Adopt in profile**: same spirit as the evidence gate |
| `requesting-code-review` | Fresh reviewer with a crafted diff, not session history | **Adopt in profile**: complements `devils-advocate` |
| `receiving-code-review` | Verify feedback before implementing; no performative agreement | **Adopt in profile**: reduces review churn |
| `using-git-worktrees` | Isolate work in a worktree or native workspace | **Adopt conditionally**: only if LibreHarness owns the lane/worktree boundary |
| `dispatching-parallel-agents` | One agent per independent problem | **Defer**: overlaps `parallel-lanes` |
| `finishing-a-development-branch` | Verify, choose merge/PR/keep/discard, clean up | **Defer**: overlaps `integrate`/`close` |
| `writing-skills` | TDD for skill text, with pressure scenarios and eval evidence | **Defer**: meta-skill; useful later for profile authoring |
| `diagnosing-superpowers` | Reads transcripts and builds an evidence-backed bug report | **Defer**: Superpowers-specific diagnosis |

The proposed profile is **8 core skills plus one conditional**:
`using-superpowers`, `brainstorming` (text only), `writing-plans`,
`test-driven-development`, `systematic-debugging`,
`verification-before-completion`, `requesting-code-review`, and
`receiving-code-review`. `using-git-worktrees` is the ninth only if the lane and
worktree boundary is stable. `executing-plans` is deferred because it calls
scripts from `subagent-driven-development`; LibreHarness keeps execution
ownership through its queue and lanes.

`brainstorming` ships a visual-companion server and a logo/telemetry path. The
profile must vendor the Markdown only, exclude `scripts/` and
`visual-companion.md`, and state that the visual companion is unavailable. That
is a deliberate text-only adaptation, not a rewrite of the method's questions.

## 3. What is strong

1. **The process is explicit and executable.** Each skill has triggers, steps,
   red flags, and rationalization tables. It does not rely on the model to
   remember a principle.
2. **Brainstorming is genuine intent discovery.** It asks what the human wants
   and why before proposing an approach. EGM starts later, with a draft. The two
   are complementary, not duplicates.
3. **Writing plans is unusually concrete.** It names files, interfaces, tests,
   expected failures, and commit steps. That is stronger than a task summary.
4. **TDD and systematic debugging are hard gates.** “Watch it fail” and “no fix
   without root cause” are checkable behaviors, not style preferences.
5. **Verification before completion is the best evidence discipline in either
   project.** It directly matches LibreHarness's evidence gate and goes further
   with a required command and output before any success claim.
6. **Review is fresh-context by construction.** The reviewer gets a diff and a
   crafted brief, not the author's session. It aligns with `devils-advocate`.
7. **The ledger and worktree model survive compaction.** Long tasks have a
   recovery map, not just chat history. The first profile defers the execution
   skills that use the ledger, but the recovery idea is worth keeping when a
   later profile owns it.
8. **It is mature and permissively licensed.** MIT, 309k stars, OpenCode plugin
   support, and a published eval lab.

## 4. What is risky

1. **Heavy context and token load.** The bootstrap plus 8 core skills and one
   conditional skill is a large instruction surface. Brainstorming and plan
   authoring can add tens of thousands of tokens before code is written.
2. **It overlaps LibreHarness almost everywhere.** Queue, goals, lanes, task
   plans, review, close, worktrees, and evidence all have a Superpowers
   counterpart. Running both without a boundary creates two sources of truth.
3. **Subagent-driven development duplicates the lane model.** A fresh
   implementer and reviewer per task is expensive and conflicts with
   LibreHarness's task ownership and integrator role. It should stay out of the
   first profile.
4. **The mandatory-skill language is brittle.** “If there is even a 1% chance”
   is intentionally aggressive. It can trigger process on small tasks, and it
   can fight an operator who wants a direct answer.
5. **Plans live in `docs/superpowers/plans/`, not the task queue.** A profile
   must either map plans into the task `Plan` section or accept a second
   artifact location.
6. **The worktree flow assumes git branches.** LibreHarness uses tasks and
   lanes; the profile must not create a second isolation model silently. The
   profile README must name which layer owns the worktree, branch, and ledger
   before `using-git-worktrees` is enabled.
7. **The content is tuned and should not be rewritten casually.** The repository
   explicitly rejects “compliance” rewrites without eval evidence. Vendoring the
   text with attribution is safer than paraphrasing it.
8. **The public evidence is adoption and behavioral compliance, not code
   quality.** 309k stars and a large eval lab show interest and process
   compliance. They do not prove better task resolution or lower cost.
9. **The eval lab is not adoptable as code.** `superpowers-evals` has no license
   at review time. Its scenarios are useful as ideas; its code cannot be copied.
10. **The full methodology can become the work.** Brainstorming, planning,
    TDD, review, and verification can consume more effort than a small task
    warrants. The profile needs a task-size boundary.
11. **Brainstorming is not text-only upstream.** It ships a visual-companion
    server, scripts, and a logo/version request path. A text-only profile must
    exclude those assets and say the visual companion is unavailable; otherwise
    the profile violates its own "no executable code or network calls" rule.
12. **Executing-plans is not standalone.** It calls workspace and review-package
    scripts from `subagent-driven-development`. Deferring that skill while
    adopting executing-plans would produce a broken inline flow. The first
    profile therefore leaves execution to LibreHarness.
13. **The ledger and the queue can disagree.** Superpowers keeps a per-plan
    `progress.md`; LibreHarness keeps task state and evidence in the queue. If
    both are active, the profile must name one as the source of truth for
    completion and treat the other as a view.

## 5. The eval lab: Quorum

`superpowers-evals` is a behavioral eval lab for Superpowers. Quorum drives real
coding-agent CLIs, including OpenCode, through conversation-like scenarios and
grades workflow compliance with a QA agent plus deterministic post-checks. It
is not a generic code benchmark and not a resolution-rate leaderboard.

What is useful:

- scenario ideas for skill triggering, worktree behavior, review quality, and
  verification reflexes;
- the distinction between “completed the conversation” and “passed the
  assessment”;
- the isolation model: per-run HOME, no host config, explicit credentials;
- the warning that live evals run agents with broad execution power.

What blocks adoption:

- no license file at review time, so its code cannot be vendored;
- it is tuned to Anthropic grading and Superpowers-specific scenarios;
- it measures workflow compliance, not whether the finished code solves a task.

Decision: **do not adopt Quorum; borrow scenario ideas only.** The local
ablation runner remains the fast review-feature check, and Harbor remains the
coding-outcome benchmark.

## 6. Comparison with EGM and current LibreHarness

| Dimension | Current LibreHarness | EGM | Superpowers |
|---|---|---|---|
| Primary unit | Task in a Markdown queue | Design spec | Skill-driven workflow |
| Upstream intent | Goal request + design gate | Brainstorm/draft | `brainstorming` interview |
| Planning | Task `Plan` + goal children | Design doc + implementation plan | `writing-plans` with exact files and tests |
| Review | Jev + conditional `devils-advocate` | Zero-context Goldfish swarm | Fresh reviewer subagent |
| Evidence | Acceptance + command evidence | Human approval + review reports | `verification-before-completion` |
| Execution | Queue, lanes, worktrees | Human-approved spec, then implement | Inline or subagent-driven |
| Weak spot | Design review is lighter than EGM | Heavy review, no execution loop | Heavy process, overlaps the queue |

The current harness is the lightest. EGM adds design rigor. Superpowers adds
end-to-end process rigor. The combination is plausible but must beat each
single profile, not just the current baseline.

## 7. Four arms

| Arm | Base | Overlay | Question |
|---|---|---|---|
| `current` | LibreHarness | none | What do we have now? |
| `egm` | LibreHarness | `profiles/egm/` | Does EGM-lite improve design review? |
| `superpowers` | LibreHarness | `profiles/superpowers/` | Does the selected process skill set improve planning and execution? |
| `both` | LibreHarness | both overlays | Do they complement or duplicate each other? |

Every arm uses the same model, OpenCode version, task fixture, and time limit.
The profile name and file hashes go in the manifest.

## 8. Metrics and adoption rule

Fast review suite:

- recall of seeded defects;
- precision, including false blockers;
- input, output, reasoning, and cache-read tokens, with cache reported separately;
- cost and wall time;
- at least three repetitions per arm.

Harbor coding subset:

- verifier reward per task;
- exceptions, especially false failures;
- input/output tokens, cost, and wall time;
- one task per arm for the pilot, with the same model and OpenCode version.

Adoption rule:

1. A profile must find at least one more seeded blocker than `current` at no
   more than twice the review tokens, with no more than one false blocker per
   review.
2. On Harbor, a profile must not reduce reward and must not add exceptions,
   cost, or wall time without a measured quality reason.
3. `both` must beat `egm` and `superpowers` separately. If it only adds cost, it
   is rejected.
4. A neutral or negative result is recorded and the profile stays optional or is
   deleted. It is not promoted into the default harness.

The current ablation runner has two arms. The `multi-arm-bench` task must add
named arms before the pilot. The pairwise schedule is:

```text
current vs egm
current vs superpowers
current vs both
both vs egm
both vs superpowers
```

"Beat" is a dominance check, not a composite score.

For a single profile against `current`:

1. no lower recall or verifier reward;
2. no new exception or failed run;
3. fewer false blockers;
4. cost within rule 1's budget: no more than twice `current`'s review tokens,
   with cost and wall time reported beside it rather than used as a second hard
   gate.

For `both` against each single profile, the cost rule is different because
`both` is a strict superset of context and is expected to cost more:

1. no lower recall or verifier reward;
2. no new exception or failed run;
3. fewer false blockers;
4. cost within a named budget: no more than the sum of the two single profiles,
   or no more than twice the cheaper single profile. State which budget applies
   before the run.

`both` is adopted only when its quality gain clears that premium. It is not
required to be cheaper than a single profile; that would make the arm
impossible to adopt by construction.

If no arm clears its rule, report the trade-off and do not adopt. The four-arm
pilot uses one Harbor task per arm as a breakage check, not as an adoption
threshold. An adoption decision that depends on Harbor needs at least three
repetitions per task or a larger task subset, with the raw data attached.

## 9. Token estimate

These are priors, not measurements.

| Arm | Expected extra context | Expected quality effect | Confidence |
|---|---|---|---|
| `current` | baseline | baseline | — |
| `egm` | +15k to +50k tokens per design/review | +3 to +8 pp on design-heavy tasks | Low |
| `superpowers` | +10k to +40k tokens per task; more for brainstorming and plans | +3 to +10 pp on multi-step tasks; near zero on small clear tasks | Low |
| `both` | +30k to +90k tokens; highest process overhead | +5 to +12 pp if the skills complement; negative if they conflict | Very low |

The likely outcome is that `superpowers` helps long, multi-step tasks and hurts
small ones, while `egm` helps ambiguous designs and does little for a clear bug
fix. The pilot should show that split rather than one blended score.

Superpowers re-injects the `using-superpowers` bootstrap after compaction. A
long task that compacts several times pays that bootstrap more than once, so the
upper end of the Superpowers and `both` ranges is more likely on long sessions.
The benchmark reports input, output, reasoning, and cache-read tokens separately;
the token total is input plus output, with cache reads shown beside it. Do not
add cache reads into the input total or the comparison will double-count.

## 10. Recommendation

Adopt into the optional `superpowers` profile:

- `using-superpowers`, `brainstorming` (Markdown only, no visual companion),
  `writing-plans`, `test-driven-development`, `systematic-debugging`,
  `verification-before-completion`, `requesting-code-review`, and
  `receiving-code-review`.
- `using-git-worktrees` only if the profile README names LibreHarness as the
  owner of the lane, worktree, and ledger boundary.

Defer:

- `executing-plans` and `subagent-driven-development`, because they call each
  other's scripts and duplicate LibreHarness execution ownership.
- `dispatching-parallel-agents`, `finishing-a-development-branch`,
  `writing-skills`, and `diagnosing-superpowers`.

Reject:

- the full Superpowers methodology as a default;
- any code from Quorum (unlicensed);
- a profile that rewrites LibreHarness's queue, goal, lane, or close contracts.

The first comparison should use the selected profile, not all 15 skills. A
full-methodology arm can be a later experiment if the selected profile shows a
signal.

## 11. What this does not prove

- No profile has been implemented or measured yet.
- No Superpowers run has been made against LibreHarness tasks.
- The quality and token estimates are priors.
- The profile selection is a judgment from the source, not an eval result.
- Quorum was reviewed from its README and repository shape, not run.
