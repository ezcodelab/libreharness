<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Hard coding run, 2026-10-31

Status: **n=3 pilot. No promotion.** The predeclared threshold was not met and
the ceiling rule triggered.

## Setup

- Harbor 0.25.0, OpenCode 1.19.5, `ollama-cloud/deepseek-v4.1-flash`.
- Suite `terminal-bench-hard-v1`: `sanitize-git-repo`,
  `large-scale-text-editing`, `git-leak-recovery`,
  `modernize-scientific-stack`, `custom-memory-heap-crash`,
  `db-wal-recovery`, `multi-source-data-merger`, `cobol-modernization`.
- Five arms: `plain`, `current`, `egm`, `superpowers`, `both`.
- Three repetitions per task per arm; randomized arm order; seed 31.
- 24 trials per arm, 120 total.

Raw jobs and `runs.csv` are archived outside the public tree.

## Results

| Arm | Solved | Rate | Exceptions | Cost USD | Tokens | Mean wall s | Test-first | Test files |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| plain | 23/24 | 96% | 20 | $0.3223 | 10,642,105 | 60.8 | 0% | 0 |
| current | 23/24 | 96% | 0 | $0.3423 | 13,961,807 | 63.3 | 0% | 0 |
| egm | 23/24 | 96% | 0 | **$0.2860** | **8,096,971** | 52.0 | 0% | 0 |
| superpowers | 23/24 | 96% | 0 | $0.3008 | 8,990,362 | 56.3 | 0% | 0 |
| both | 23/24 | 96% | 0 | $0.4668 | 19,710,568 | 91.5 | 0% | 0 |

Per task:

| Task | plain | current | egm | superpowers | both |
|---|---:|---:|---:|---:|---:|
| sanitize-git-repo | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| large-scale-text-editing | 3/3 | 2/3 | 2/3 | 3/3 | 2/3 |
| git-leak-recovery | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| modernize-scientific-stack | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| custom-memory-heap-crash | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| db-wal-recovery | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| multi-source-data-merger | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| cobol-modernization | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

## Paired result

Every candidate minus plain has the same per-task shape:

- mean difference: **+0.0 percentage points**
- 95% task-clustered interval: **[-12.5, +12.5] pp**
- improved/regressed/tied: **1/1/6**

The improvement is `sanitize-git-repo` (plain 2/3, harness 3/3). The regression
is `large-scale-text-editing` (plain 3/3, current/EGM/both 2/3). Superpowers
passes both.

The `large-scale-text-editing` failures are not byte mismatches. The harness
arms produced a working macro file that transformed the data and passed the
efficiency checks, but omitted the required `:wq` or `:x` exit command. The
verifier requires that exact command. This is a workflow compliance failure, not
a formatting one.

## Ceiling rule

Six of eight tasks are 3/3 for every arm. The suite is at ceiling for those
tasks. The interval is a warning about uncertainty, not an estimate of
real-world quality. More repetitions on those six tasks cannot create
separation.

## Test behavior

No arm wrote a test on the hard tasks, so test-first is 0% wherever a source
write was observable. The tasks do not require test authoring. The separate
local test-writing task still passes all five arms at 1.0 with
`test_first = 1`; that result is unchanged.

## Decision

No profile is promoted. The threshold required two more solved tasks, no task
regression, a positive lower confidence bound, and the cost/wall budget. None
was met:

- resolution is tied at 23/24;
- the interval crosses zero;
- there is one task regression;
- the ceiling rule makes the six all-pass tasks uninformative.

Plain has 20 benign agent-exit exceptions on solved tasks; the LibreHarness arms
have none. That is the only consistent operational difference, and it is not a
resolution win.

## Next

The next suite should replace the ceiling tasks, not repeat them:

- `gpt2-codegolf` and `llm-inference-batching-scheduler` for long, ambiguous
  implementation work;
- `make-mips-interpreter` or `make-doom-for-mips` for large multi-file work;
- `path-tracing` or `compile-compcert` for deep build/debug loops;
- `dna-assembly` or `protein-assembly` for constraint-heavy work;
- keep `sanitize-git-repo` and `large-scale-text-editing` as exact-content
  controls;
- add one workflow-compliance check for explicit output/exit requirements.

Run those with the same five arms, n=3, randomized order. Keep resolution,
exceptions, cost, and wall time separate. Predeclare the threshold again before
the run, and reject a suite where most tasks are 3/3 for every arm.
