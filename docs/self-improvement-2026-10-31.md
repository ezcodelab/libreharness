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
Do not treat the means as precise.

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

> Report every independent material gap, not only the single root cause.
> Separate confirmed defects from conditional risks, and include both when
> material.

The rerun, three repetitions, same fixture and model:

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
| `egm` | Optional, not default | Highest recall and lowest cost, but 2 false blockers per review. Fix the false-blocker rate before promoting it. |
| `superpowers` | Optional, not default | Zero false blockers but lower review recall than current. The review fixture does not exercise its coding workflow. |
| `both` | Optional, not default | Ties EGM on recall and has the best precision, but 1.33 false blockers and about twice EGM's tokens and dollars. It beats current on recall and precision, but it is a trade-off, not a dominant winner. |

No profile is promoted to the default harness. The default remains the base
LibreHarness workflow.

## What this does and does not show

It shows:

- the ablation runner can isolate the host config and compare four arms on the
  same fixture;
- the Harbor adapter can apply each profile and complete a task without an
  exception;
- EGM has a strong recall signal on this fixture;
- the combined profile is the most precise of the high-recall arms, with 1.33 false blockers per review;
- a profile change can be measured and rejected when it fails the gate.

It does not show:

- that any profile improves general coding quality;
- that the review result generalizes beyond one synthetic spec;
- that the Harbor result separates the arms;
- that three repetitions and one model are enough for a public claim.

## Next

1. Add a false-blocker column to the runner and score the saved findings with it.
2. Expand the review fixture set beyond one spec, including a clean spec to
   measure false positives on no-defect input.
3. Run at least three Harbor tasks per arm, with n=3, before promoting a profile.
4. Test the EGM false-blocker fix: require a source, failure path, and missing
   guard for every blocker, and rerun.
5. Keep the default unchanged until a larger run shows a stable win.

Raw data stays in the ignored local results directory and is archived outside
the public tree. No private path or credential is in this report.
