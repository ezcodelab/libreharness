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
