<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Expanded coding pilot, 2026-10-31

Status: **pilot only. Not proof and not an “objectively best” claim.** One
repetition per arm, eight Terminal-Bench tasks, one model.

## Setup

- Harbor 0.25.0, OpenCode 1.19.5, `ollama-cloud/deepseek-v4.1-flash`.
- Tasks: `break-filter-js-from-html`, `sqlite-db-truncate`,
  `sanitize-git-repo`, `fix-code-vulnerability`, `sqlite-with-gcov`,
  `code-from-image`, `cobol-modernization`, `multi-source-data-merger`.
- Arms: `plain`, `current`, `egm`, `superpowers`, `both`.
- Seed 23; randomized arm order; one attempt per task.
- Runner: [`bench/coding.py`](../bench/coding.py); suite:
  [`bench/coding-suite.json`](../bench/coding-suite.json).

The five-arm test-writing task is separate:
[`bench/coding-tasks/test-first-bugfix`](../bench/coding-tasks/test-first-bugfix).
The earlier three-task pilot is in
[`coding-pilot-2026-10-31.md`](coding-pilot-2026-10-31.md).

## Results

| Arm | Solved | Rate | Exceptions | Cost USD | Tokens | Mean wall s | Test-first | Test files |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| plain | **8/8** | **100%** | 6 | $0.0791 | 1,861,186 | 39.9 | 0% | 0 |
| current | 7/8 | 88% | 0 | $0.0879 | 3,143,822 | 77.2 | 0% | 0 |
| egm | 7/8 | 88% | 0 | **$0.0607** | **1,330,511** | 36.0 | 0% | 0 |
| superpowers | **8/8** | **100%** | 0 | $0.1237 | 3,851,192 | 40.6 | 0% | 0 |
| both | **8/8** | **100%** | 0 | $0.1503 | 8,372,324 | 115.6 | 0% | 0 |

Per task:

| Task | plain | current | egm | superpowers | both |
|---|---:|---:|---:|---:|---:|
| break-filter-js-from-html | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| sqlite-db-truncate | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| sanitize-git-repo | 1.0 | **0.0** | **0.0** | 1.0 | 1.0 |
| fix-code-vulnerability | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| sqlite-with-gcov | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| code-from-image | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| cobol-modernization | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| multi-source-data-merger | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

The two failures are real verifier failures on `sanitize-git-repo`: the agents
changed quoting/formatting in the decontaminated files, and the verifier
requires the exact decontaminated content, not just secret removal. No secret
was left behind; the task fails on the byte-level comparison.

## Paired result

`current - plain`, paired by task:

- mean difference: **-12.5 percentage points**
- 95% task-clustered bootstrap interval: **[-37.5, +0.0] pp**
- improved/regressed/tied: **0/1/7**

`egm - plain` has the same resolution result: -12.5 pp, CI [-37.5, +0.0].

`superpowers - plain` and `both - plain` are 0 pp because both solve all eight
tasks. They are not better on resolution, and both cost more.

## Test behavior

No arm wrote a test file on the Terminal-Bench tasks, so the test-first metric
is 0% wherever a source write was observable. These tasks do not require test
authoring. The separate local task does:

- all five arms scored 1.0;
- all five wrote a regression test (`test_files_changed = 1`);
- all five were test-first by the heuristic (`test_first = 1`);
- the verifier confirmed the test fails on the baseline and passes on the fix.

That local result shows the metric works; it does not separate the arms.

## Decision

No profile is promoted, and the expanded run does not support a claim that
LibreHarness is better than stock OpenCode.

- **Plain** solves all eight tasks, but records six benign agent-exit
  exceptions on solved tasks. It is the cheapest 8/8 arm.
- **Current** and **EGM** solve seven of eight; both regress on
  `sanitize-git-repo`.
- **Superpowers** solves eight of eight but costs more than plain.
- **Both** solves eight of eight but costs about twice plain and is much slower,
  driven by a long `cobol-modernization` run.

The current harness is not objectively better on this suite. It removes the
benign exceptions but loses one task; the combined profile regains the task at
a higher cost. That is a trade-off, not a win.

## What the proof protocol requires next

1. n=3 per task per arm; one repetition is not a stable estimate.
2. A test-requiring task in the main suite, not only the separate local task.
3. More design/review-heavy tasks from the expanded set, with per-task results.
4. A held-out set not used to choose a profile.
5. A paired interval whose lower bound is above zero, within the predeclared
   cost and exception budget.

Until then, the only defensible statement is: on these eight tasks, at this
model and version, plain, superpowers, and both solved 8/8; current and EGM
solved 7/8. No arm is objectively best.
