<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Process lessons

One dated entry per completed task. Keep it short: what surprised us, what it
cost, the rule that changes the next decision, and the doc that now carries it.

## 2026-10-31 - Harbor adapter lifecycle hook

Surprise: `configure()` was never called by Harbor 0.25.0; the framework calls
`setup()`. The passing "harness" pilot was effectively stock OpenCode because
the overlay upload never ran.

Cost: one misleading pilot arm and a false benchmark signal.

Rule: prove a framework lifecycle hook from the framework source or a run log,
not from a unit test that calls the method directly. A subclass method that is
never invoked is dead code.

Doc updated: `harbor_agent/README.md`, `tests/test_harbor_adapter.py`.

Promote-to-global: yes. The same trap applies to any plugin, hook, or callback.

## 2026-10-31 - Fast feature ablation

Surprise: keyword scoring can reward a finding that repeats the spec's own
positive wording, and a live benchmark that exits 0 on a failed arm can turn a
crash into a negative result.

Cost: one review round and a test rewrite.

Rule: a benchmark must distinguish "found nothing" from "did not run". Failed
arms exit non-zero and are excluded from scoring. Match rules need the gap
polarity, not just the topic word. Parse the assistant text event, not the raw
JSONL stream.

Doc updated: `bench/ablation.md`, `tests/test_ablation.py`.

Promote-to-global: yes. Silent success is worse than a visible failure.

## 2026-10-31 - EGM review

Surprise: EGM's public evidence is adoption and fixture tests, not a measured
quality gain. The Harbor adapter is integration glue, not a product moat.

Cost: none beyond review time.

Rule: label quality and token estimates as unmeasured, and run a seeded-defect
ablation before adopting a review feature. Adoption is not efficacy.

Doc updated: `docs/egm-review.md`.

Promote-to-global: yes. Separate use, interest, and measured effect.

## 2026-10-31 - Four-arm pilot isolation

Surprise: the first four-arm run inherited the host OpenCode config, so the
auto-intake plugin turned the review prompt into a LibreHarness task and the
model edited queue files instead of returning JSON. The run measured the host
harness, not the prompts.

Cost: one invalid 12-run batch, discarded before recording.

Rule: isolate `XDG_CONFIG_HOME` and `XDG_STATE_HOME`, run `opencode
--standalone`, and require a JSON-only answer. A test must assert the standalone
flag, the temporary cwd, and the isolated config/state dirs. A profile change
that gains recall but breaks the false-blocker gate is reverted, not kept.

Doc updated: `bench/ablation.md`, `docs/self-improvement-2026-10-31.md`.

Promote-to-global: yes. A benchmark that loads the host harness is measuring the
wrong thing.

## 2026-10-31 - Benchmark feedback

Surprise: the second fixture's first regex set credited a data-model finding to
the key-exposure defect, and the aggregate table hid failed rows as zero-recall
runs. Tightening the regexes changed the fixture-B ranking.

Rule: report false positives by severity, exclude errored rows from aggregate
means, require gap polarity in every fixture rule, and keep per-run rows and the
min-max spread. A scoring change is rescored from saved findings, not presented
as a new model run.

Doc updated: `bench/ablation.md`, `docs/self-improvement-2026-10-31.md`.

Promote-to-global: yes. A benchmark's labels are part of the instrument; audit
them before trusting a ranking.

## 2026-10-31 - Coding runner path bugs

Surprise: the coding wrapper pointed `PYTHONPATH` at `bench/` and passed a
relative Harbor `-o` while running with `cwd=bench/`. Every LibreHarness arm
failed to import, and Harbor wrote jobs to `bench/bench/results` while the
wrapper read `bench/results`.

Rule: test the actual subprocess env and cwd, not only the parser. Point
`PYTHONPATH` at the repo root, use an absolute jobs directory, and assert both
in a live-path test. Add the wrong output path to `.gitignore` as defense in
depth.

Doc updated: `bench/coding.md`, `tests/test_coding.py`, `.gitignore`.

Promote-to-global: yes. A benchmark wrapper that cannot import the thing under
test is measuring nothing.

## 2026-10-31 - Five-arm coding pilot

Surprise: every LibreHarness arm solved 3/3 on the three-task pilot, while stock
plain solved 2/3. The paired difference is +33.3 pp but the task-clustered 95%
interval is [+0.0, +100.0] pp, so it is inconclusive. No arm wrote tests, so the
test-first metric says nothing about Superpowers on these tasks.

Rule: a three-task, one-repetition coding pilot is a smoke, not proof. A
test-first metric needs a task that requires a failing test first. Do not
promote a profile from a positive point estimate whose interval touches zero.

Doc updated: `docs/coding-pilot-2026-10-31.md`, `bench/coding.md`.

Promote-to-global: yes. Report the interval and the missing metric, not just the
solved count.

## 2026-10-31 - Expanded coding suite

Surprise: on eight Terminal-Bench tasks, stock plain solved 8/8 while current
and EGM solved 7/8; superpowers and both solved 8/8 but cost more. The two
harness failures were byte-level `sanitize-git-repo` formatting changes, not
leaked secrets. No Terminal-Bench task required test authoring; the separate
local test-first task passed 1.0 on all five arms.

Rule: broaden the task set before adding repetitions. A profile that removes
benign exceptions can still lose a task; report per-task regressions, not only
the aggregate. Test-first needs a task that requires a test.

Doc updated: `docs/coding-expanded-2026-10-31.md`, `bench/coding.md`.

Promote-to-global: yes. A larger task set can reverse a smaller pilot's story.

## 2026-10-31 - Exact-byte regression

Surprise: the `sanitize-git-repo` verifier compares the contaminated files to
exact decontaminated copies and forbids changing any other file. Current/EGM
removed the secrets but reformatted YAML and quoted values; Superpowers also
changed an unlisted Slack webhook and then rewrote an embedded token line.

Rule: use targeted replacement, replace only the value itself, preserve every
other byte, and change only the files or acceptance set the task names. Report
an extra issue outside that set instead of fixing it. Do not weaken the verifier.

Doc updated: `docs/coding-exact-bytes.md`, `AGENTS.md`.

Promote-to-global: yes. Exact-content tasks punish helpful scope expansion.

## 2026-10-31 - Hard suite ceiling

Surprise: six of eight hard tasks were 3/3 for every arm; every arm solved
23/24. The only separation was sanitize-git-repo (plain 2/3, harness 3/3) and
large-scale-text-editing (plain 3/3, current/EGM/both 2/3). The large-scale
failures omitted the required `:wq`/`:x` exit command.

Rule: when most tasks are all-pass, the suite is at ceiling; replace the tasks,
do not add repetitions. Check explicit format and exit requirements before
finishing. Keep the predeclared threshold and report a tie.

Doc updated: `docs/coding-hard-run-2026-10-31.md`.

Promote-to-global: yes. A ceilinged benchmark cannot rank harnesses.

## 2026-11-01 - Hard-v2 is not a ceiling, but not a win

Surprise: the replacement suite broke the all-pass ceiling. `dna-assembly` was
the only clear profile gain (plain 0/3, profiles 1-2/3). `large-scale-text-editing`
was a regression for every LibreHarness arm (plain 2/3, profiles 1/3). Still no
profile met the threshold: current tied plain at 19/24, EGM/both/superpowers
solved 18/24.

Rule: when the suite separates, inspect the task-level wins and losses before
adding repetitions. A single strong task gain does not outweigh multiple
regressions. Keep the predeclared threshold; a tie is not a promotion.

Doc updated: `docs/coding-hard-v2-2026-11-01.md`.

Promote-to-global: yes. Task-level variance is the signal; aggregate ties hide
it.

## 2026-11-01 - Public-tree cleanup has a history caveat

Surprise: deleting experiment files in a new commit does not remove them from
the existing Git history, so a public repository created from this repository's
current history would still expose them.

Cost: one cleanup pass and a release gate that must be resolved before
publishing.

Rule: a clean tree is not a clean history. If the operator accepts the old
history, say so explicitly and keep only the current tree clean; otherwise
prepare the public snapshot from a fresh history or a clean export. Keep the
public process ledger as a template and archive experiment lessons outside it.

Doc updated: `brain/references/benchmarks/libreharness/README.md`.

Promote-to-global: yes. A clean tree is not a clean history.
