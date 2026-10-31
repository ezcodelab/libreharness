<!-- SPDX-License-Identifier: MIT -->
# Coding benchmark

Status: **pilot result recorded; not proof.** This is the coding-outcome
benchmark for LibreHarness. It runs a fixed Terminal-Bench suite through Harbor
and records the verifier reward, exceptions, tokens, cost, wall time, and a
test-first heuristic.

## Why this exists

The review-ablation suite measures whether a review prompt finds seeded design
defects. It cannot show that a harness solves coding tasks. This runner uses
real Terminal-Bench tasks with verifier rewards, so a comparison is grounded in
completed work rather than review prose.

The headline result is still **Terminal-Bench 2.0 resolution rate** with raw
Harbor jobs. This wrapper adds repeatability and a few process metrics; it does
not replace the official benchmark.

## Suite

`bench/coding-suite.json` fixes:

- dataset `terminal-bench@2.0`;
- tasks `break-filter-js-from-html`, `sqlite-db-truncate`,
  `sanitize-git-repo`;
- arms `plain` (stock OpenCode), `current` (LibreHarness base), `egm`,
  `superpowers`, and `both`;
- model, OpenCode version, Harbor version, endpoint, and API format.

Change the suite file, not Python constants, to add a task or arm.

## Commands

Dry run, no model:

```sh
python3 bench/coding.py --dry-run
```

Live run, one attempt per arm:

```sh
python3 bench/coding.py --live --out bench/results/coding-pilot
```

The wrapper prints a cost warning, randomizes the arm order with `--seed`, and
writes `manifest.json` and `runs.csv` under the output directory. Harbor's job
directories stay under that output, outside the public tree.

Use `--repetitions 3` for a comparison. The pilot default is 1 because a
three-task, five-arm run at n=3 is already 45 trials.

Paired analysis:

```sh
python3 bench/analyze.py --input bench/results/coding-pilot/runs.csv \
  --baseline plain --candidate current --bootstrap 2000 --seed 0
```

The result of the first pilot is in
[`docs/coding-pilot-2026-10-31.md`](../docs/coding-pilot-2026-10-31.md).

## Metrics

| Metric | Source |
|---|---|
| `reward` | Harbor verifier |
| `exception` | Harbor agent exception |
| `cost_usd` | Harbor agent result |
| `input_tokens`, `output_tokens`, `cache_tokens` | Harbor agent result |
| `wall_seconds` | Agent execution start and finish |
| `test_first` | Heuristic from the agent's write/edit/patch tool calls |
| `test_files_changed` | Unique test paths in those tool calls |
| `source_files_changed` | Unique source paths in those tool calls |
| `error` | Wrapper or Harbor failure; kept separate from a zero reward |

`test_first` is `1` when the first test-file write appears before the first
source-file write, `0` when the source file comes first, and `unknown` when the
agent made no observable write. It is a heuristic, not proof of TDD:

- shell redirection, heredocs, and tools other than write/edit/patch are not
  observed;
- a test written after a source file can still be a valid test, but it is not
  test-first;
- test quality is not graded here. The verifier says whether the task works.

Test quality and human correction time are later metrics. A reviewer can add a
manual column to the pilot report; do not invent a number.

## Fairness

- Same dataset, tasks, model, OpenCode version, Harbor version, and endpoint
  across arms.
- One task per container; the wrapper asks Harbor for `-n 3` (one per task).
- Randomized arm order; seed and run order are in the manifest.
- A failed arm is recorded, not dropped. The wrapper exits non-zero for a
  wrapper/Harbor error or an unsolved trial with an agent exception. A solved
  trial with a benign agent exception keeps its verifier reward, is shown in the
  table, and does not fail the run by itself.
- One task is a smoke. One repetition is a pilot. The protocol in
  [`docs/benchmark-proof.md`](../docs/benchmark-proof.md) defines what a
  publishable comparison needs.

## Limits

- Three tasks are not the Terminal-Bench leaderboard.
- The test-first heuristic can miss shell-based test creation.
- Test quality, review findings, and human correction time are not automated.
- Harbor reward is binary per task; the wrapper does not invent a composite
  score.
- The wrapper records a `plain` arm and four LibreHarness arms; adding another
  harness is a suite entry with its own agent import path.

## Next

1. Run the three-task pilot at n=1 and inspect failures.
2. Add a fourth task that requires tests, so test-first behavior is exercised.
3. Run n=3 with the same suite and publish raw jobs and `runs.csv`.
4. Add a paired analysis with a bootstrap confidence interval before making a
   claim.
