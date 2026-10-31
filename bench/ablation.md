<!-- SPDX-License-Identifier: MIT -->
# Feature ablation benchmark

Status: **scaffold and self-check, no live result.** This is a fast supplement
to the Harbor/Terminal-Bench headline, not a public score.

## What it answers

Does adding one review feature find more seeded design defects without a
disproportionate false-positive or token cost?

The runner compares one or more declarative prompt arms on the same seeded
design specification. The default is two:

| Arm | Feature |
|---|---|
| `baseline` | The current review prompt |
| `candidate` | The baseline plus a zero-context comprehension step |

For a four-arm comparison, pass `--arm` once per arm. The runner records every
arm in the same manifest and `runs.csv`.

The output is recall, precision, input and output tokens, cache-read tokens,
cost, and wall time. Output tokens include reasoning tokens; cache reads are
reported separately. It is designed for an iteration loop of minutes, not a
full coding task. A failed or timed-out arm is recorded with an `error` and the
runner exits non-zero; it is not treated as a negative review result.

## Why one spec instead of a code task

A full Harbor task took 7 to 13 minutes in the pilot and cost up to $0.09. A
review-only fixture runs in seconds to a few minutes and isolates the review
step. Each arm runs in a fresh temporary workspace with its own XDG config and
state directories, so host plugins, AGENTS.md, agents, commands, and skills do
not load. The host auth store stays in the data directory. Every arm sees the
same input. That makes it practical to test a prompt or
checklist change before adopting this kind of EGM feature. Harbor remains the
public headline because only it measures whether the finished code solves a
task.

## Layout

```text
bench/
├── ablation.py              runner, scorer, self-check
├── features/ablation/
│   ├── baseline.json        current review prompt
│   └── comprehension.json   candidate prompt
└── fixtures/ablation/
    ├── spec.md              seeded design document
    ├── defects.json         five seeded defects and match rules
    └── sample-findings.json deterministic scoring sample
```

Adding a feature is a data change: copy a feature JSON file, change its `label`
and `prompt`, and pass it with `--candidate` or as a named `--arm`. No Python
constants to edit.

## Commands

Dry run, no model call:

```sh
python3 bench/ablation.py --dry-run
```

Four-arm dry run:

```sh
python3 bench/ablation.py --dry-run --out bench/results/four-arm-dry \
  --arm current=bench/features/ablation/baseline.json \
  --arm egm=bench/features/ablation/egm.json \
  --arm superpowers=bench/features/ablation/superpowers.json \
  --arm both=bench/features/ablation/both.json
```

The four prompts are data files. `comprehension.json` is the older two-arm
candidate; the four-arm names use `egm.json`, `superpowers.json`, and
`both.json`. Arm names are lowercase letters, digits, and hyphens. Duplicate
names and missing feature files are rejected before any model call. `--arm`
overrides `--baseline` and `--candidate`.

The manifest records the fixture hash, defect hash, model, feature labels,
prompt hashes, repetition count, timeout, and planned commands.

Self-check, no model call:

```sh
python3 bench/ablation.py --self-check
```

It scores `sample-findings.json` and prints recall, precision, true positives,
false positives, tokens, and wall time. The sample carries expected values, so
a scoring regression exits non-zero.

Live run:

```sh
python3 bench/ablation.py --live \
  --model ollama-cloud/deepseek-v4.1-flash \
  --out bench/results/ablation-2026-10-31
```

`--live` prints a cost warning and invokes OpenCode once per arm. It requires an
explicit model and a working provider credential. Raw session JSON and per-run
prompts stay under the output directory.

## Scoring

Each seeded defect has a regular expression. A finding is a true positive when
its text matches a defect that has not been matched yet. A finding that matches
no defect is a false positive. A repeated finding for an already matched defect
is counted as a duplicate and does not change precision.

```text
recall    = matched defects / seeded defects
precision = true positives / (true positives + false positives)
```

The match rules are a deterministic proxy, not a substitute for reading the raw
findings. A finding can use different words and still be correct; a broad regex
can also accept a vague finding. Read the per-run `findings.json` before making
a decision.

## Host smoke, 2026-10-31

This is a host smoke, not a benchmark result. It ran on OpenCode 2.2.4, not the
Harbor pin of 1.19.5, with one repetition and the current fixture.

| Arm | Recall | Precision | Tokens | Cost USD | Wall s |
|---|---:|---:|---:|---:|---:|
| baseline | 60% | 27% | 17,232 | $0.0041 | 17.8 |
| candidate | 60% | 38% | 17,024 | $0.0040 | 11.6 |

Both arms matched D1, D3, and D4 under the regex. Manual review of the raw
findings shows both also identified D2 (the create/poll method problem), but the
regex did not credit it; D5 was missed. The candidate produced fewer false
positives on the same seeded recall, which is a useful signal but not enough to
adopt. A v2 fixture with clearer match rules and three repetitions is needed
before a claim.

Raw data: `bench/results/ablation-2026-10-31-live/` (ignored by git).

The four-arm pilot and its rejected improvement are in
[`docs/self-improvement-2026-10-31.md`](../docs/self-improvement-2026-10-31.md).

## Adoption rule

Adopt an arm only when, against the current or baseline arm:

- it finds at least one more seeded blocker;
- it uses no more than twice the baseline review tokens;
- it adds no more than one false blocker per review;
- the raw findings support the score.

When comparing `both` against two single overlays, use the separate cost budget
in `docs/superpowers-review.md`, not this single-arm rule. Otherwise record the
result as neutral or negative and do not adopt the feature. A neutral result is
a valid outcome.

## Limits

- One synthetic spec and one model do not generalize.
- The fixture is visible to the reviewer; this measures review behavior, not
  resistance to a hidden benchmark.
- The runner isolates XDG config and state. The host data and cache directories
  still hold auth, the local database, storage, and cached packages; they do not
  hold instructions, but they make the environment machine-specific. Record the
  OpenCode version, provider, and host setup for a comparison.
- Regex scoring is coarse. It rewards the seeded vocabulary. The rules require
  the gap wording, not just the topic word, but they are still a proxy.
- One repetition is a smoke, not a statistical result. Use three repetitions
  before a claim, and still report the sample size.
- The runner does not replace Harbor, Terminal-Bench, hidden tests, or human
  review.
- The 2026-10-31 host smoke is one repetition on a different OpenCode version.
  It is not a quality claim. Do not cite a gain from this scaffold.

For the EGM review that motivated the comprehension arm, see
[`docs/egm-review.md`](../docs/egm-review.md). For the public benchmark, see
[`docs/benchmark-tools.md`](../docs/benchmark-tools.md) and
[`bench/protocol.md`](protocol.md).
