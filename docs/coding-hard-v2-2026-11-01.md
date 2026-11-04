<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Hard-v2 coding run, 2026-11-01

Status: **n=3 pilot. No promotion.** The suite is no longer a ceiling, but the
paired result is inconclusive and every profile has task regressions.

## Setup

- Harbor 0.25.0, OpenCode 1.19.5, `ollama-cloud/deepseek-v4.1-flash`.
- `terminal-bench-hard-v2`: `sanitize-git-repo`,
  `large-scale-text-editing`, `gpt2-codegolf`,
  `llm-inference-batching-scheduler`, `dna-assembly`,
  `protein-assembly`, `make-mips-interpreter`, `path-tracing`.
- Five arms: `plain`, `current`, `egm`, `superpowers`, `both`.
- Three repetitions per task per arm; randomized order; seed 41.
- 24 trials per arm, 120 total.

Raw jobs and `runs.csv` are archived outside the public tree.

## Results

| Arm | Solved | Rate | Exceptions | Cost USD | Tokens | Mean wall s | Test-first | Test files |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| plain | 19/24 | 79% | 21 | **$0.9464** | **45,426,106** | 277.9 | 0% | 0 |
| current | 19/24 | 79% | 1 | $1.0722 | 47,001,153 | 283.4 | 0% | 0 |
| egm | 18/24 | 75% | 1 | $1.1677 | 59,723,048 | **257.1** | 0% | 0 |
| superpowers | 18/24 | 75% | 2 | $1.3977 | 72,438,712 | 370.7 | 0% | 0 |
| both | 18/24 | 75% | 1 | $1.1438 | 52,904,367 | 330.2 | 0% | 0 |

Per task:

| Task | plain | current | egm | superpowers | both |
|---|---:|---:|---:|---:|---:|
| sanitize-git-repo | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| large-scale-text-editing | 2/3 | 1/3 | 1/3 | 1/3 | 1/3 |
| gpt2-codegolf | 3/3 | 2/3 | 3/3 | 2/3 | 2/3 |
| llm-inference-batching-scheduler | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 |
| dna-assembly | 0/3 | 2/3 | 2/3 | 1/3 | 2/3 |
| protein-assembly | 3/3 | 2/3 | 2/3 | 2/3 | 3/3 |
| make-mips-interpreter | 3/3 | 3/3 | 2/3 | 3/3 | 1/3 |
| path-tracing | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

The suite is no longer six-way all-pass. Task-level signals:

- `dna-assembly`: plain 0/3, current/EGM/both 2/3, superpowers 1/3. The only
  clear profile gain.
- `large-scale-text-editing`: plain 2/3, every LibreHarness arm 1/3. The exact
  output/exit requirement is still fragile.
- `make-mips-interpreter`: plain/current/superpowers 3/3, EGM 2/3, both 1/3.
- `gpt2-codegolf`: plain/EGM 3/3, current/superpowers/both 2/3.
- `sanitize-git-repo`: every LibreHarness arm 3/3, plain 2/3.
- `path-tracing` is 3/3 everywhere and is still a ceiling task.

## Paired result

`current - plain`:

- mean difference: **-0.0 percentage points**
- 95% task-clustered interval: **[-20.8, +25.0] pp**
- improved/regressed/tied: **2/3/3**

`egm - plain` is the same point estimate and interval. `superpowers - plain` and
`both - plain` are **-4.2 pp** with intervals that cross zero.

The interval is based on only eight tasks and three repetitions. It is a warning
about uncertainty, not a precise estimate of real-world performance.

## Exceptions and cost

Plain recorded 21 benign agent-exit exceptions on solved tasks, plus one
network error. The LibreHarness arms recorded one or two exceptions each,
mostly setup/timeout errors. This removes false exceptions but does not produce
a resolution win.

Plain is the cheapest arm and has the fewest tokens. EGM is the fastest on mean
wall time. `both` and `superpowers` cost more and do not solve more tasks.

## Decision

No profile is promoted.

The predeclared threshold required two more solved tasks, no task regression, a
positive lower interval bound, and the cost/wall budget. None was met:

- all arms are within one solved task of each other;
- each profile has at least two task regressions;
- the interval crosses zero;
- cost and tokens are higher than plain for every profile.

`current` ties plain at 19/24 but is not better. `egm` has the strongest single
task gain (`dna-assembly`) and a regression on `large-scale-text-editing`,
`make-mips`, and `protein-assembly`.

## Test behavior

No arm wrote a test on these tasks; the test-first rate is 0%. The separate
local test-writing task still passes all five arms at 1.0 with
`test_first = 1`.

## Next

The useful next work is task-level, not more repetitions:

1. Understand why plain fails `dna-assembly` 0/3 while the profiles succeed.
   That is the only clear profile gain; it is a candidate lesson.
2. Fix the `large-scale-text-editing` regression: the output and exit
   requirement are still missed by every LibreHarness arm.
3. Inspect the `make-mips-interpreter` regression for `both`.
4. Add one or two more tasks that are not 3/3 for every arm; `path-tracing` is
   still a ceiling.
5. Keep the predeclared threshold. A tie at 19/24 is not a promotion.

## Artifacts

- This report.
- Raw `runs.csv` and Harbor jobs are archived outside the public tree.
- Commit to be recorded with this report.
