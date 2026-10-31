<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Four-arm self-improvement pilot, 2026-10-31

Status: **pilot only. Not a public benchmark result.** One synthetic review
fixture, three repetitions on the fast suite, and one Harbor task per arm. The
numbers show what this setup can measure, not a general quality claim.

## Setup

Fast suite:

- Host OpenCode 2.2.4, `ollama-cloud/deepseek-v4.1-flash`.
- Three repetitions per arm.
- The runner isolates `XDG_CONFIG_HOME` and `XDG_STATE_HOME` per run, so host
  plugins, `AGENTS.md`, agents, commands, and skills do not load.
- The prompt includes the spec inline and asks for JSON only.
- Fixture SHA-256: `e2a6ed8cc508a727143964080a37334273b45ba36304ebe7b346a14d4fdb8a39`.
- Defect list SHA-256: `3ee06dfeb0ebaf77c0a0ad9360a7fbb9678fa5668ec076210c60f24a54fcbdfb`.

Harbor:

- Harbor 0.25.0, OpenCode 1.19.5, same model.
- One task, `break-filter-js-from-html`, one repetition per arm.
- The profile was passed with `--ak profile=<name>` and recorded in
  `agent/profile.json`.

Arms:

| Arm | Overlay |
|---|---|
| `current` | Base LibreHarness, no profile |
| `egm` | EGM comprehension and readiness (convergence is multi-round and not exercised here) |
| `superpowers` | Selected Superpowers evidence and verification skills |
| `both` | EGM comprehension and readiness plus the selected Superpowers skills |

## Fast review suite

| Arm | Recall | Precision | False blockers / review | Tokens (3 reps) | Cost USD (3 reps) | Mean wall s |
|---|---:|---:|---:|---:|---:|---:|
| current | 67% | 36% | 1.33 | 50,177 | $0.0263 | 67.5 |
| egm | **87%** | 40% | 2.00 | **27,368** | **$0.0110** | **19.9** |
| superpowers | 60% | 31% | **0.00** | 46,059 | $0.0193 | 36.3 |
| both | **87%** | **44%** | 1.33 | 56,240 | $0.0219 | 43.5 |

False blockers are counted from the saved findings, not the runner's CSV. The
runner reports false positives; a false-positive finding is a false blocker only
when its severity is `blocker`. A blocker-labeled finding that matches a seeded
major is a true positive under this rule.

The `both` row was rerun after review because its first prompt omitted the EGM
readiness checklist. The corrected prompt is the fair superset of the EGM and
Superpowers arms; the rerun is the number reported here.

What the table says:

- **EGM** has the highest recall and the lowest token, cost, and wall time. It
  also has two false blockers per review, which fails the one-false-blocker
  gate. It is the best recall/cost arm, not a clean adopt.
- **Superpowers** is below the current arm on recall and precision on this
  review-only fixture. It has zero false blockers. This fixture is not the work
  Superpowers is designed for; the Harbor task is the better signal for it.
- **Both** ties EGM on recall and has the best precision, but it has 1.33 false
  blockers and costs about twice EGM's tokens and dollars. It is a balanced
  trade-off, not a dominant winner.

The sample is small. The per-repetition spread is wide: for example, EGM recall
runs from 80% to 100%, and the current arm's wall time runs from 12.6s to 118.6s.
The console and `runs.csv` preserve every per-run row and print the min-max
spread; the tables here are means for readability. With three repetitions,
report the range, not a confidence interval.

### Second fixture

A second independently authored spec (`spec-b.md`, API-key rotation) was run
with the same four arms, three repetitions, seed 7, randomized order.

| Arm | Recall | Precision | False blockers / review | Tokens (3 reps) | Cost USD (3 reps) | Mean wall s |
|---|---:|---:|---:|---:|---:|---:|
| current | **80%** | 82% | 0.33 | 43,673 | $0.0149 | 24.0 |
| egm | **80%** | 70% | 0.67 | 34,746 | **$0.0125** | 21.7 |
| superpowers | 67% | **86%** | **0.00** | 30,968 | $0.0173 | 40.1 |
| both | **80%** | 64% | **0.00** | **30,445** | $0.0168 | 38.9 |

The first fixture-B score used looser regexes and over-credited one data-model
finding to the key-exposure defect. The rules were tightened, and the saved
findings were rescored with `bench/ablation.py --rescore`, which writes
`runs-rescored.csv`, without a model rerun. The table above is the corrected
score. This is a scoring correction, not a new model result.

The two fixtures do not agree on one winner:

- **EGM** holds 87% recall on A and 80% on B and is the cheapest, but its
  precision moves from 40% to 70% and its false blockers from 2.0 to 0.67.
- **Both** holds 87% recall on A and 80% on B, but its precision moves from 44%
  to 64% and its token cost is about twice EGM's on A.
- **Superpowers** is below current on recall on both fixtures, but has the best
  precision and zero false blockers on B.
- **Current** is the reference, not a candidate, and it is competitive on B.

This is still two fixtures and one model. It is a reason to keep testing, not a
reason to promote.

## Harbor one-task check

| Arm | Reward | Exception | Cost USD | Input | Output | Wall |
|---|---:|---|---:|---:|---:|---:|
| current | 1.0 | none | 0.0172 | 309,684 | 14,920 | 61.9s |
| egm | 1.0 | none | 0.0119 | 393,294 | 10,754 | 65.6s |
| superpowers | 1.0 | none | 0.0080 | 95,338 | 4,278 | 18.9s |
| both | 1.0 | none | 0.0068 | 136,702 | 4,554 | 91.8s |

All four arms passed the verifier with no exception. This task is too easy to
separate quality: the result is a breakage check, not a quality signal. It does
show that the profile overlays do not break the adapter, authentication, or the
exit contract.

## Improvement attempt

The weakest measured axis was Superpowers recall on the review fixture: 60%,
below the current arm's 67%. I added a rule to the Superpowers profile and the
matching review prompt:

> report every independent material gap, not only the single root cause

The existing evidence rule stayed in place; the only added instruction was the
every-gap requirement. The rerun, three repetitions, same fixture and model:

| Superpowers | Recall | Precision | False blockers / review | Tokens | Cost USD | Wall s |
|---|---:|---:|---:|---:|---:|---:|
| before | 60% | 31% | 0.00 | 46,059 | $0.0193 | 36.3 |
| after | 73% | 29% | 1.33 | 53,222 | $0.0235 | 43.7 |

The change bought 13 percentage points of recall, lost 2 points of precision,
and added 1.33 false blockers per review. It fails the one-false-blocker gate,
so it was **reverted**. The before state is restored. This is a negative result
and it is recorded as one.

## Decision

| Arm | Decision | Reason |
|---|---|---|
| `current` | Keep | Baseline. |
| `egm` | Optional, not default | 87% recall on A and 80% on B, and the lowest cost, but precision moves from 40% to 70% and false blockers from 2.0 to 0.67. Fix the false-blocker rate before promoting it. |
| `superpowers` | Optional, not default | Below current on recall on both fixtures, but the best precision and zero false blockers on B. The review fixtures do not exercise its coding workflow. |
| `both` | Optional, not default | 87% recall on A and 80% on B, but precision moves from 44% to 64% and cost is about twice EGM's on A. It is not a dominant winner. |

No profile is promoted to the default harness. The default remains the base
LibreHarness workflow.

## Predeclared promotion rule for the next experiment

This is fixed before the next run, not after seeing its numbers.

Minimum design:

- at least three independently authored fixtures, including one clean
  no-defect fixture;
- at least two coding tasks that exercise planning, test-first work, or
  debugging;
- three repetitions per arm, randomized order, fixed model and OpenCode version;
- held-out fixtures not used to choose the change.

A profile is promoted to the default only when:

1. recall does not regress on any seeded fixture;
2. false blockers stay at or below one per review on every fixture;
3. precision is not below the current arm on any fixture;
4. tokens are no more than twice the current arm, and cost or wall time are not
   worse without a measured quality reason;
5. on the coding tasks, reward does not regress and at least one of test-first
   behavior, test quality, regression avoidance, or review findings improves;
6. the result repeats on the held-out fixtures.

If a profile wins recall but loses precision or false blockers, it stays an
optional profile. A single aggregate win is not a promotion.

## Deferred: coding-purpose Superpowers benchmark

The one Harbor task is a breakage check, not a Superpowers quality measure. A
separate task should run a small coding set that exercises what Superpowers is
for:

- does the agent write a failing test before production code;
- are the tests meaningful, not assertions on implementation details;
- does the task complete, and do existing tests still pass;
- how many regressions or review findings appear;
- how much human correction time is needed;
- tokens, cost, and wall time beside those outcomes.

That task should use the same Harbor/Terminal-Bench path and keep the one-task
run as a smoke only.

## What this does and does not show

It shows:

- the ablation runner can isolate the host config and compare four arms on the
  same fixture;
- the Harbor adapter can apply each profile and complete a task without an
  exception;
- no arm dominates current across both fixtures: EGM and both trade precision
  for recall, and Superpowers trades recall for precision;
- the per-run spread is visible, and no profile advantage is stable enough to
  promote;
- a profile change can be measured and rejected when it fails the gate.

It does not show:

- that any profile improves general coding quality;
- that the review result generalizes beyond two synthetic specs;
- that the Harbor result separates the arms;
- that three repetitions, two fixtures, and one model are enough for a public
  claim.

## Next

1. Add a clean no-defect fixture and a third independently authored seeded spec.
2. Add the coding-purpose task set described above; one Harbor task remains a
   smoke.
3. Test the EGM false-blocker fix: require a source, failure path, and missing
   guard for every blocker, and rerun across all fixtures.
4. Keep the default unchanged until the predeclared rule passes on held-out
   fixtures.

Raw data stays in the ignored local results directory and is archived outside
the public tree. No private path or credential is in this report.
