<!-- SPDX-License-Identifier: MIT -->
# Benchmark

Status: **local workflow supplement; the external headline uses Harbor and
Terminal-Bench.**

The public comparison is **Terminal-Bench 2.0 via Harbor**, which already
supports OpenCode and reports resolution rate plus tokens and cost. See
[`docs/benchmark-tools.md`](../docs/benchmark-tools.md). This directory is now a
fast local smoke/regression suite, not the public headline.

A two-task Harbor pilot is recorded in
[`pilot-2026-10-30.md`](pilot-2026-10-30.md). It is not a full benchmark and
shows no quality delta.

For a fast before/after check of one review feature, use the seeded-spec
ablation runner in [`ablation.md`](ablation.md). It compares two or more
declarative prompt arms, scores findings against five seeded defects, and runs
in minutes.
It is a feature-level supplement, not a public score.

For coding outcomes, [`coding.py`](coding.py) runs a fixed Terminal-Bench suite
through Harbor across stock OpenCode and the LibreHarness profiles. It records
reward, exceptions, tokens, cost, wall time, and a test-first heuristic. See
[`coding.md`](coding.md). The first five-arm pilot is in
[`docs/coding-pilot-2026-10-31.md`](../docs/coding-pilot-2026-10-31.md); it is
a pilot, not proof.

The local suite answers three questions:

- A: does the harness improve completed work at acceptable cost, with Jev
  disabled in both arms?
- B: did the publication refactor change behavior, with Jev enabled in both
  arms?
- C: does Jev improve review and planning enough to justify its cost?

The full design, arms, task set, metrics, and threats are in
[`protocol.md`](protocol.md). The short version: eight fixed tasks, three
repetitions per task per arm, one model and environment per arm, hidden tests
scored outside the agent workspace.

The headline is **pass@1 at the fixed budget**: tasks whose first repetition
passes all hidden tests divided by tasks in the suite, times 100. Cost and wall
time are secondary. Run the `plain` arm first as the before baseline, then the
`harness` arm.

No performance claim may be made from this directory until the raw data, the
manifest, and the analysis are published or made available to reviewers. A
neutral or negative result is published with the same care as a positive one.

## Layout

```text
bench/
├── README.md          this file
├── protocol.md        frozen design, task set, metrics, analysis, threats
├── runner.py          plan or run one task repetition
├── ablation.py        fast review-feature ablation and scoring
├── ablation.md        how the ablation works and how to add a feature
├── coding.py          fixed Terminal-Bench coding runner
├── coding.md          coding metrics and test-first limits
├── coding-suite.json  fixed tasks and five arms
├── features/ablation/ declarative arm prompts
├── analyze.py         summarize a results directory
├── tasks/             one fixed prompt and rubric per category, B1 to B8
├── fixtures/          fixture repositories and the ablation spec
└── results/           generated run data, ignored except .gitkeep
```

`tasks/` contains the prompts and rubrics. `fixtures/` is empty until the
fixtures are built and frozen; each task file describes the fixture it expects.
`results/` is empty by design. Generated data is ignored by git except
`.gitkeep`; reviewed summaries are added deliberately after review.

## Dry run

From the repository root:

```sh
python3 bench/runner.py --help
python3 bench/runner.py --dry-run
python3 bench/runner.py --dry-run --task B4 --arm harness-jev --repetition 2
```

A dry run prints the planned command and writes a sample
`manifest.json` under `bench/results/dry-run/`. It does not call a model,
contact a provider, or touch a fixture.

Defaults are `--task B1`, `--arm harness`, `--repetition 1`, and
`--out bench/results/dry-run`. Valid arms are `plain`, `harness`,
`pre-refactor`, `rc`, `harness-no-jev`, and `harness-jev`. Comparison C arms
accept only B1, B4, B7, and B8.

## Live runs

Live execution is opt-in:

```sh
python3 bench/runner.py --live --task B1 --arm harness --repetition 1 \
  --model provider/model --workspace path/to/fresh/fixture-checkout \
  --out bench/results/YYYY-MM-DD
```

`--live` prints a cost warning before it runs, because it invokes a paid model
provider. It also requires an explicit `--model` and `--workspace`. The runner
writes the prompt, session JSON, diff, stderr, and timing for the run. It does
not set up the fixture, hidden tests, or the environment; those steps are
described in the protocol and are not automated yet.

Never run a live benchmark against a production checkout. Use a fresh clone of
the fixture in a temporary directory.

## Score

```sh
python3 bench/score.py --help
python3 bench/score.py --input bench/results/YYYY-MM-DD --arm plain
python3 bench/score.py --input bench/results/YYYY-MM-DD --baseline plain --candidate harness
python3 bench/analyze.py --input bench/results/YYYY-MM-DD
```

With no `runs.csv`, the scripts print a clear no-results message and exit 0.
They never substitute sample numbers or a composite score.

## Data policy

- Fixtures are small original repositories written for this benchmark. No
  customer code, customer data, or private repository content.
- No API keys, auth headers, tokens, or personal paths in captured data.
  Redact before storage, then scan again before publication.
- Raw session JSON can contain paths and provider metadata. It stays private or
  is sanitized before publication.
- Per-run patches are published only when they contain fixture code alone.
- Public release contains `manifest.json`, `runs.csv`, `summary.csv`,
  `analysis.md`, and `analysis.py`, plus a data-availability statement for
  reviewers.
- Results are reported per task and per category, including failures and
  timeouts. Do not pool categories without also showing each category.

## What is not here

- No fixtures yet.
- No hidden tests yet.
- No evaluator automation yet.
- No runs, no summary, no result of any kind.

The protocol is frozen before the first run. Record hashes of the protocol and
task files, then do not change them after seeing results.
