<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Benchmark proof protocol

Status: **protocol only. No harness is claimed to be objectively best.** This
document defines what such a claim would require, so the benchmark cannot drift
into a slogan after the fact.

## The claim

LibreHarness may be called **objectively better** than another harness only when
all of the following hold on the same public suite:

1. the primary outcome is Terminal-Bench 2.0 **resolution rate**;
2. the comparison uses the same tasks, model, OpenCode version, Harbor version,
   endpoint, time limits, and environment;
3. the task set is fixed before the run and is not selected from the results;
4. there are at least three repetitions per task per arm, with randomized order;
5. a paired analysis by task shows a positive advantage whose 95% confidence
   interval excludes zero;
6. the advantage is not bought with a predeclared-unacceptable increase in
   tokens, cost, wall time, exceptions, or regressions;
7. raw jobs, `runs.csv`, the manifest, task hashes, and the analysis are
   available to a reviewer.

If any condition is missing, the result is a **pilot**, a **regression check**,
or a **trade-off**, not proof.

“Better than any other” is not a universal claim. It means better than every
arm actually entered on the same suite. A new harness is compared by adding an
arm, not by asserting a different benchmark.

## Arms

The default comparison:

| Arm | What it is |
|---|---|
| `plain` | Stock OpenCode, no LibreHarness |
| `current` | LibreHarness base, no profile |
| `egm` | LibreHarness with the EGM profile |
| `superpowers` | LibreHarness with the selected Superpowers profile |
| `both` | LibreHarness with both profiles |

Another harness is a suite entry with its own Harbor agent import path and, if
needed, a profile. It gets the same tasks and settings.

## Suites

**Coding headline.** Terminal-Bench 2.0 via Harbor. The eight-task
[`bench/coding-suite.json`](../bench/coding-suite.json) set is a fixed smoke and
pilot suite, not a leaderboard. A publishable claim uses the full dataset or a
fixed, publicly named subset large enough to estimate resolution rate; the
subset, task hashes, and selection rule are frozen before the run.

**Review signal.** The seeded review fixtures in
[`bench/fixtures/ablation/`](../bench/fixtures/ablation/) measure whether a
review finds defects. They are secondary evidence: a review win does not prove
coding quality, and a coding win does not prove review quality. The clean
no-defect fixture measures false positives; the seeded fixtures measure recall
and precision by severity.

## Metrics

Primary:

- resolution rate: tasks whose verifier passes / tasks run;
- exceptions and timeouts, reported separately and counted as failures in the
  headline;
- tokens per solved task and cost per solved task;
- wall time per task.

Secondary:

- test-first rate from the coding runner’s heuristic;
- test files changed and source files changed;
- review recall, precision, false blockers, false majors, and false nits;
- human correction time, only when a human records it with a stated method.

No composite score. Do not blend a quality gain with a cost saving into one
number.

## Before reporting a number

Before a measured number becomes a claim, answer these seven questions from a
run, not from a guess about the code. If an answer is unknown, the result is
inconclusive, not a win.

1. **What limits it?** Name the resource or code path that bounds the result,
   such as a core, a lock, the disk, the network, or the load generator. Get it
   from a profile or system counters, not from reading the code. If you cannot
   say why the result is not twice as good, you do not know what you measured.
2. **Were both sides tuned?** Compare release builds, production flags, data
   sizes, caches, connection pools, and versions. If one side ran on defaults,
   you compared configurations, not implementations.
3. **Does it break a limit?** Check bytes per second against disk and network
   bandwidth, operations against core count, and the saved time against the
   time the changed piece took.
4. **Did it error?** Count failures, timeouts, retries, and wrong output. Fast
   rejections and slow retries can both make a number meaningless.
5. **Does it reproduce?** For a standalone number, run alternating sides at
   least five times, then report the median and range. A gap smaller than
   run-to-run variation is not a difference. A benchmark claim still follows
   the repetition rule below.
6. **Does it matter end to end?** Measure the path a user waits on with
   realistic data and concurrency. A helper that is 1% of the request cannot
   make the request 100% faster.
7. **Did the work happen?** Confirm the code path ran inside the timed region:
   the request reached the server, the rows were written, the bytes were read,
   and the result was used. Lazy code and timeouts can produce numbers for work
   that never happened.

The verdict is faster, slower, no measurable difference, or inconclusive. Give
the number with its unit, run count, range, and limiter. Keep the detailed
evidence in a linked artifact, not only in prose.

The checklist format is adapted from Cursor's pstack (MIT). The statistical
protocol in this document remains authoritative for a benchmark claim.

## Statistical rule

The unit of analysis is the task. Repetitions estimate within-task noise; they
do not create new tasks.

- Pair each arm with the baseline on the same task.
- Use a task-clustered bootstrap for the resolution-rate difference, or a
  paired test appropriate to binary outcomes.
- Report the point estimate, the 95% interval, the number of tasks, and the
  number of repetitions.

`bench/analyze.py` implements the task-clustered bootstrap for a coding
`runs.csv`:

```sh
python3 bench/analyze.py --input bench/results/coding/runs.csv \
  --baseline plain --candidate current --bootstrap 2000 --seed 0
```
- A claim needs the lower bound of the interval above zero. A point estimate
  with an interval crossing zero is inconclusive.
- Report the per-task table and the flipped tasks. An average cannot hide a
  regression on a task class.

The local eight-task suite cannot support a claim. Its interval will be too
wide, and it is a smoke by design.

## Predeclared promotion rule

A hard-suite run uses `terminal-bench-hard-v2` (eight tasks), five arms, and
n=3. The baseline is `plain`. The threshold is fixed before the run:

- a candidate must solve **at least two more tasks** than plain (25 percentage
  points on eight tasks), with **no task regression**;
- the paired 95% task-clustered interval must have a **lower bound above zero**;
- total cost must be no more than **1.25x plain**, mean wall no more than
  **1.5x plain**, and there must be **no unsolved exception**;
- a solved trial with a benign agent exception is recorded but does not count
  as a failed task;
- the result must repeat on held-out tasks before promotion.

**Ceiling rule.** If plain solves seven or eight of the eight tasks, or if every
arm solves all eight, the pair is at ceiling and the result is uninformative for
that comparison. More repetitions on a ceiling task do not create separation.
The report must say so and the profile is not promoted from it.

No composite score. A profile that wins one aggregate but loses a task class
stays optional. A neutral or negative result is published with the same care as
a positive one.

## Data availability

Publish or make available to a reviewer:

- `manifest.json` with the suite, tasks, arm, model, OpenCode, Harbor, seed,
  order, and code commit;
- raw Harbor jobs with per-trial `result.json` and trajectories;
- `runs.csv` with per-trial metrics;
- task and fixture hashes;
- the analysis script and its output;
- a limitations section and the failed or excluded runs.

Remove secrets, credentials, personal paths, and private data. Keep sanitized
raw data, not only summary tables.

## Falsification and threats

The claim is falsified by:

- a lower confidence bound at or below zero;
- a cost or exception increase outside the predeclared budget;
- a regression on a task class that the aggregate hides;
- a result that only appears on tasks used to choose the change;
- a run that loaded a different model, harness, or task version.

Known threats:

- model and provider drift between arms;
- task contamination or visibility of hidden tests;
- benchmark gaming and reward hacking;
- non-deterministic agent behavior and small task sets;
- the test-first heuristic missing shell-based writes;
- review prompts being judged by regex labels rather than a second reviewer;
- selection of a favorable subset after seeing results.

## What this does not prove

A benchmark can show that one harness solved more tasks under a fixed budget. It
cannot prove that the harness is better for every repository, model, or task
class. It cannot replace a human review of the trajectories, the failures, and
the maintainability cost.

No result in this repository is an “objectively best” claim yet. The coding
runner, review suite, and this protocol are the machinery for one.
