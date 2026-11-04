<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Coding benchmark pilot, 2026-10-31

Status: **pilot only. Not proof and not an “objectively best” claim.** One
repetition per arm, three Terminal-Bench tasks, one model.

This report covers the original three-task pilot and the separate local
test-writing task. The expanded eight-task Terminal-Bench run is a different
run and is not included here until it finishes.

## Setup

- Harbor 0.25.0, OpenCode 1.19.5, `ollama-cloud/deepseek-v4.1-flash`.
- Terminal-Bench 2.0 tasks: `break-filter-js-from-html`,
  `sqlite-db-truncate`, `sanitize-git-repo`.
- Five arms: `plain` (stock OpenCode), `current` (LibreHarness base), `egm`,
  `superpowers`, `both`.
- Seed 11; randomized arm order; one attempt per task per arm.
- Runner: [`bench/coding.py`](../bench/coding.py); suite:
  [`bench/coding-suite.json`](../bench/coding-suite.json).

Raw data stays in the ignored local results directory and is archived outside
the public tree. The table below is reproducible from `runs.csv`.

## Results

| Arm | Solved | Rate | Exceptions | Cost USD | Tokens | Mean wall s | Test-first | Test files |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| plain | 2/3 | 67% | 2 | $0.0352 | 1,254,009 | 45.9 | 0% | 0 |
| current | **3/3** | **100%** | **0** | $0.0355 | 651,373 | **27.2** | 0% | 0 |
| egm | **3/3** | **100%** | **0** | **$0.0349** | **632,447** | 31.5 | 0% | 0 |
| superpowers | **3/3** | **100%** | **0** | $0.0354 | 1,500,341 | 39.9 | 0% | 0 |
| both | **3/3** | **100%** | **0** | $0.0585 | 1,982,310 | 97.1 | 0% | 0 |

Per task:

| Arm | break-filter | sqlite-db-truncate | sanitize-git-repo |
|---|---:|---:|---:|
| plain | 1.0 | 1.0 | 0.0 |
| current | 1.0 | 1.0 | 1.0 |
| egm | 1.0 | 1.0 | 1.0 |
| superpowers | 1.0 | 1.0 | 1.0 |
| both | 1.0 | 1.0 | 1.0 |

The plain arm’s two solved tasks also recorded a benign
`NonZeroAgentExitCodeError` from OpenCode’s exit path. The verifier reward is
kept; the exception is shown, not counted as a failed task.

## Paired result

`current` minus `plain`, paired by task:

| Task | plain | current | Difference |
|---|---:|---:|---:|
| break-filter-js-from-html | 100% | 100% | +0 pp |
| sqlite-db-truncate | 100% | 100% | +0 pp |
| sanitize-git-repo | 0% | 100% | +100 pp |

Mean difference: **+33.3 percentage points**. Task-clustered 95% bootstrap
interval: **[+0.0, +100.0] pp**. Improved/regressed/tied: **1/0/2**.

The interval touches zero and the task count is three, so this is
**inconclusive**. `egm`, `superpowers`, and `both` show the same +33.3 pp
against plain because they also solve all three tasks. No pair separates the
four LibreHarness arms on resolution; the differences are cost and time.

## Test-first

No arm wrote a test file on these tasks, so the test-first rate is 0% wherever
the heuristic could observe a source write. The tasks do not require a failing
test first, and `break-filter` and `sqlite` are shell-work tasks. This metric
does not exercise the Superpowers TDD behavior. A test-requiring task is
required before it can say anything about Superpowers.

## Local test-writing task

The Terminal-Bench tasks do not require the agent to author a test, so a local
Harbor task was added: `bench/coding-tasks/test-first-bugfix`. The verifier
requires a new regression test, checks that it fails against the baseline code,
passes against the fixed code, and that the existing test is unchanged.

| Arm | Reward | Test-first | Test files | Existing test | Cost USD | Tokens |
|---|---:|---:|---:|---|---:|---:|
| plain | 1.0 | 1 | 1 | unchanged | $0.00125 | 58,366 |
| current | 1.0 | 1 | 1 | unchanged | $0.00362 | 82,134 |
| egm | 1.0 | 1 | 1 | unchanged | $0.00358 | 81,629 |
| superpowers | 1.0 | 1 | 1 | unchanged | $0.00259 | 76,187 |
| both | 1.0 | 1 | 1 | unchanged | $0.00395 | 107,501 |

All five arms wrote a regression test, kept the existing test, and fixed the
bug. The plain arm again recorded a benign agent-exit exception after a solved
task; the LibreHarness arms did not. This task shows the test-first metric
works; it does not separate the arms.

## Decision

No profile becomes the default.

- `current` and `egm` both solve 3/3. `current` is fastest; `egm` has slightly
  fewer tokens and slightly lower cost, but is slower. Neither separates on
  resolution.
- `superpowers` solves 3/3 but uses more tokens than current/EGM and does not
  show test-first behavior on these tasks.
- `both` solves 3/3 but costs about 1.7x current and is the slowest arm.
- `plain` loses one task and records two benign exceptions; the paired interval
  still includes zero.

The pilot suggests the LibreHarness arms do not reduce resolution on these
tasks. It does not show an improvement.

## What the proof protocol requires next

1. At least three repetitions per task per arm.
2. More tasks, including at least one that requires a failing test first.
3. A held-out task set not used to choose a change.
4. A paired interval whose lower bound is above zero, with the predeclared
   cost and exception budget.
5. Raw jobs, `runs.csv`, manifest, and analysis available to a reviewer.

Only then can a result support a relative “better” claim. “Best” remains
undefined until another harness is entered on the same suite under the same
protocol.
