<!-- SPDX-License-Identifier: MIT -->
# Local benchmark protocol

Status: **local supplement only, no results.** The public headline is
Terminal-Bench 2.0 via Harbor. Use this smaller suite for fast harness
regression, not for a public comparison. See
[`docs/benchmark-tools.md`](../docs/benchmark-tools.md).

This file is frozen before the first local live run. Record its hash and the
hashes of the task files in the run manifest. Do not change tasks after seeing
results.

## Purpose

Measure the harness against a plain build agent, measure the publication
refactor for behavior parity, and measure Jev on the tasks where advisory
review has leverage. The benchmark is small and its power is low. It is a
release gate and an honest public measurement, not a leaderboard.

## Claims policy

A claim needs all of the following:

1. this pre-registered protocol;
2. the fixed task set and fixture commits;
3. the raw run data and per-run directories;
4. the analysis script and its output;
5. the manifest with versions, model snapshot, and price snapshot;
6. a statement of limitations.

No claim of the form "the harness is better". Report the observed result with
the task set, model, and date: "on these eight tasks, with this model and date,
the observed hidden-test pass rate was X versus Y". Negative and neutral
results are published with the same care as positive ones.

## Comparisons

| ID | Question | Arms | Tasks | Unit | Primary outcome | Use |
|---|---|---|---|---|---|---|
| A | Does the harness improve completed work at acceptable cost? | `plain` vs `harness`, Jev disabled in both | B1 to B8 | One task run | pass@1 at the fixed budget | Publication claim and README performance section |
| B | Did the publication refactor change behavior? | `pre-refactor` vs `rc`, Jev enabled in both | B1 to B8 | One task run | Parity in pass rate, tokens, and time | Release gate and regression threshold |
| C | Does Jev justify its cost? | `harness-no-jev` vs `harness-jev` | B1, B4, B7, B8 | One task run | Hidden-test pass, review send-backs, defects caught before submission | Jev claim, default enablement, docs |

Run counts at n = 3:

- A: 8 tasks x 2 arms x 3 repetitions = 48 runs.
- B: 8 tasks x 2 arms x 3 repetitions = 48 runs.
- C: 4 tasks x 2 arms x 3 repetitions = 24 runs.
- Total: 120 runs. A four-run pilot is excluded from analysis.

Comparison C uses B1 bug fix, B4 review, B7 security, and B8 multi-file because
those categories give advisory review something concrete to catch. The same
model, provider, and environment are used across arms within a comparison. Jev
is the only intended difference in C.

## Fixed task set

Eight tasks, one per category. Fixtures are small original repositories under
about 5,000 lines with deterministic tests. Hidden tests are not visible in the
agent workspace. Each task file under `bench/tasks/` contains the exact prompt,
acceptance checks, and hidden checks. Prompts are identical across arms.

| ID | Category | Fixture idea | Acceptance | Hidden check |
|---|---|---|---|---|
| B1 | Bug fix | Cursor pagination over a stable sort returns one item twice at a page boundary | Pages are correct, no duplicate, existing tests pass | Boundary, empty-page, and last-page tests |
| B2 | Feature | Authenticated CSV export that streams a large result | Auth enforced, correct content type, large result works | Route, auth, and streaming tests |
| B3 | Refactor | Deduplicate email and username validation without behavior change | Public behavior identical, duplication removed | Existing suite plus snapshot comparison |
| B4 | Review | Seeded diff with an auth bypass, a missing rollback, and a flaky test | All three found, no invented blockers | Rubric scored by two reviewers |
| B5 | Docs | Document a new `--dry-run` flag, update examples, fix a stale link | Commands work, links resolve, no stale text | Docs lint and command smoke test |
| B6 | Tests | Add retry and backoff tests that catch a seeded mutation | Tests fail on the mutated implementation | Mutation run |
| B7 | Security | Fix path traversal in a file download route | Exploit blocked, legitimate access preserved | Exploit and access tests |
| B8 | Multi-file | Add a cache TTL flag through parser, service, docs, and tests | End-to-end behavior correct, docs updated | Integration test |

Each task packet contains the fixture commit, the exact prompt, allowed tools,
the 30-minute time limit, the token cap, and the acceptance rubric. Record the
token cap in the manifest per run.

## Arms and environment

| Arm | Comparison | Harness | Jev |
|---|---|---|---|
| `plain` | A | Minimal `AGENTS.md`, no queue, skills, commands, or local plugins | off |
| `harness` | A | Release candidate with queue, skills, commands, local plugins | off |
| `pre-refactor` | B | Pre-refactor snapshot with public-safe environment shims | on |
| `rc` | B | Release candidate | on |
| `harness-no-jev` | C | Release candidate | off |
| `harness-jev` | C | Release candidate | on |

Controls:

- Same OpenCode version, model ID, provider, temperature and top-p defaults,
  tool set, network policy, machine class, container image, and time limit.
- Fresh temporary `HOME`, fresh fixture clone, and fresh queue state for every
  run. Do not reuse caches, sessions, or queue state between runs.
- Reset repository state to the fixture commit before every run.
- Run one session at a time. No parallel runs.
- Randomize order with a seeded block design by task. Record the seed and the
  order in the manifest.
- Pin the Jev model, endpoint, prompt hash, and threshold profile. If Jev is
  unavailable, record comparison C as skipped. Do not substitute a different
  model and do not drop the arm silently.
- The evaluator runs hidden tests automatically. The analyst receives arm
  labels only after metrics are computed.
- An infrastructure failure is a failure. At most one retry is allowed for a
  provider outage or runner crash; mark the retry.
- If the model or provider changes during the study, stop and restart the
  affected block. Do not mix snapshots.
- Comparison B: the pre-refactor snapshot is exported with the same public-safe
  environment shims. A task that still needs a private path is excluded and
  recorded.

## Standard metric

The headline number is **pass@1 at the fixed benchmark budget**:

```text
pass@1 = tasks whose first repetition passes all hidden tests
         --------------------------------------------------- x 100
                      number of tasks in the suite
```

The fixed budget is the task packet's 30-minute limit and token cap. Use the
first repetition for each task. Cost, wall time, review send-backs, and human
interventions are reported beside the score, not blended into it. There is no
composite score and no weighting.

The **before** number is the `plain` arm on the same eight tasks, same model,
same environment, and same budget. A person considering LibreHarness should
record that baseline first. The **after** number is the `harness` arm. Report
the absolute scores and the delta in percentage points.

```sh
python3 bench/score.py --input bench/results/YYYY-MM-DD --arm plain
python3 bench/score.py --input bench/results/YYYY-MM-DD --baseline plain --candidate harness
```

A score without the raw `runs.csv`, manifest, and task hashes is not publishable.

## Metrics

| Metric | Definition | Source |
|---|---|---|
| `task_pass` | All acceptance checks pass, 0 or 1 | Evaluator |
| `hidden_pass` | All hidden tests pass, 0 or 1 | Hidden test run |
| `pass_at_1` | First repetition per task passes all hidden tests / tasks in suite x 100 | `bench/score.py` |
| `wall_seconds` | Start to final answer, excluding queue wait | Runner |
| `input_tokens` | Prompt tokens | Session JSON |
| `output_tokens` | Completion tokens | Session JSON |
| `cache_read_tokens` | Cached input tokens read | Session JSON |
| `cache_write_tokens` | Cached input tokens written | Session JSON |
| `cost_usd` | Tokens times the recorded price snapshot, including cache read and write prices | Analysis script |
| `review_sendbacks` | Review rounds that required code changes | Session events plus manual tally |
| `human_interventions` | Messages after the fixed prompt that change scope, plan, or code | Session events |
| `files_changed` | Files in the final diff | `git diff --numstat` |
| `lines_added` | Added lines in the final diff | `git diff --numstat` |
| `lines_removed` | Removed lines in the final diff | `git diff --numstat` |
| `defects_found` | B4 only, 0 to 3 | Rubric |
| `defect_caught_before_submit` | B1, B7, B8: 1 if the seeded or hidden defect was caught before final submission | Rubric |
| `jev_cost_usd` | Jev calls times the recorded price snapshot | Jev usage or analysis estimate |
| `jev_latency_seconds` | Time spent in Jev calls | Runner |

`review_sendbacks` and `human_interventions` are workflow metrics, not
substitutes for hidden tests. In comparison A the plain control has no queue or
review loop, so both are expected to be zero by construction. In comparison C
the control is the harness without Jev, so its send-backs and interventions are
the non-Jev review baseline and are not assumed to be zero. B4 scores
`defects_found`; B1, B7, and B8 score `defect_caught_before_submit`, so Jev is
measured on all four C tasks.

Timeouts and crashes count as failures and are also reported separately in a
sensitivity analysis.

## Capture

- The runner invokes headless OpenCode with the fixed prompt and records start
  and end times.
- Capture the session JSON through the OpenCode session API or the pinned
  version's equivalent export command. Record the exact command in the
  manifest so capture is reproducible.
- Write one CSV row per run. Keep raw session JSON, diff, hidden-test output,
  stderr, and timing in a per-run directory.
- Record the model price snapshot and provider from the manifest, not from
  memory.
- Never store API keys, auth headers, or personal paths in captured data.
  Redact before storage, then scan again before publication.
- The evaluator writes `hidden-tests.txt` outside the agent workspace after the
  run ends. The agent never sees it.

## Raw data layout

```text
bench/results/YYYY-MM-DD/
├── README.md
├── manifest.json
├── runs.csv
├── summary.csv
├── analysis.md
├── analysis.py
└── runs/
    └── <run_id>/
        ├── session.json
        ├── prompt.txt
        ├── diff.patch
        ├── hidden-tests.txt
        ├── stderr.txt
        └── timing.json
```

`manifest.json` records the date, harness commit, pre-refactor commit, OpenCode
version, model ID, provider, price snapshot, container image digest, seeds,
operator, token cap, and any deviations. For comparison C it also records the
Jev endpoint, model, prompt hash, threshold profile, and whether the live or
mock transport was used.

`runs.csv` uses the metric names above plus `run_id`, `comparison`, `arm`,
`task_id`, `repetition`, and `order`.

Public release contains `manifest.json`, `runs.csv`, `summary.csv`,
`analysis.md`, and `analysis.py`. Per-run patches are published only when they
contain fixture code alone. Raw session JSON stays private or is sanitized.
Reviewers get access under a documented data-availability statement.

## Analysis

- Per task: median and interquartile range for continuous metrics; pass rate
  with numerator and denominator.
- Aggregate: paired by task, median difference, bootstrap 95 percent
  confidence interval, and Wilcoxon signed-rank when its assumptions are
  reasonable. With eight tasks, statistical power is low; report that.
- Report every run, including failures and timeouts. Show the sensitivity
  analysis with and without infrastructure failures.
- Separate quality (pass rate, hidden tests, defects found) from efficiency
  (time, tokens, cost).
- For comparison C, report hidden-test pass, review send-backs,
  `defect_caught_before_submit` for B1, B7, and B8, `defects_found` for B4,
  and Jev cost and latency separately. A Jev result that finds no extra defect
  is still a result.
- Do not pool categories without also showing per-category results.
- State the exact observed numbers and the limitations. Do not generalize past
  the fixed task set, model, and date.

## Threats to validity

- Small sample and low statistical power.
- Model and provider drift during the study, including a Jev model or prompt
  change in comparison C.
- Task leakage or benchmark overfitting by the harness author.
- The operator knows Jev's thresholds better than the control reviewer.
- Learning and order effects across repetitions.
- Operator familiarity with the harness but not the control.
- The control may be under-specified, which can exaggerate the treatment.
- Cost excludes human review time.
- Review task scoring is partly subjective.
- Machine, network, and provider load variance.
- Publication bias toward positive results.

## Reproducibility

- Pin the harness commit, model snapshot, OpenCode version, container digest,
  price table, Jev endpoint, Jev model, prompt hash, and thresholds.
- Keep the runner and analysis scripts in `bench/`. Captured metrics are not
  entered by hand; rubric scores are recorded by the evaluator.
- Publish seeds and the randomization log.
- Document a one-command rerun for the analysis.
- State what cannot be reproduced, such as a retired model version.

## Data policy

- Fixtures are original and contain no customer data, customer code, or
  private repository content.
- No secrets or personal paths in any captured file.
- Raw sessions are private by default and sanitized before any publication.
- The benchmark repository must not be a production checkout.
