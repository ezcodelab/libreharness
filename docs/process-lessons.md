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
