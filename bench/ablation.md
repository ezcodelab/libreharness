<!-- SPDX-License-Identifier: MIT -->
# Feature ablation benchmark

Status: **pilot run on two seeded fixtures, not a public score.** The clean
fixture and fixture C are added but not yet run across all arms. This is a fast
supplement to the Harbor/Terminal-Bench headline.

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

The output is recall, precision, false positives split by severity, input and
output tokens, cache-read tokens, cost, and wall time. Output tokens include
reasoning tokens; cache reads are reported separately. The console prints the
aggregate table, every per-run row, and the min-max spread; `runs.csv` keeps the
same per-run data. It is designed for an iteration loop of minutes, not a full
coding task. A failed or timed-out arm is recorded with an `error` and the
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
│   ├── comprehension.json   older two-arm candidate
│   ├── egm.json             EGM-lite review prompt
│   ├── superpowers.json     Superpowers evidence prompt
│   ├── superpowers-gaps.json rejected every-gap candidate
│   └── both.json            combined review prompt
└── fixtures/ablation/
    ├── spec.md              seeded design document A
    ├── defects.json         five seeded defects for A
    ├── spec-b.md            seeded API-key rotation design B
    ├── defects-b.json       five seeded defects for B
    ├── spec-c.md            seeded webhook delivery design C
    ├── defects-c.json       five seeded defects for C
    ├── spec-clean.md        no-defect design
    ├── defects-clean.json   empty defect list
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
`both.json`. `superpowers-gaps.json` keeps the rejected every-gap hypothesis as
a separate candidate. Arm names are lowercase letters, digits, and hyphens.
Duplicate names and missing feature files are rejected before any model call.
`--arm` overrides `--baseline` and `--candidate`.

Second fixture:

```sh
python3 bench/ablation.py --dry-run --out bench/results/four-arm-b \
  --fixture bench/fixtures/ablation/spec-b.md \
  --defects bench/fixtures/ablation/defects-b.json \
  --arm current=bench/features/ablation/baseline.json \
  --arm egm=bench/features/ablation/egm.json \
  --arm superpowers=bench/features/ablation/superpowers.json \
  --arm both=bench/features/ablation/both.json
```

`--seed` randomizes the run order and records it in the manifest. The seed and
the `run_order` list are written even for a dry run. The manifest also records
the fixture hash, defect hash, model, feature labels, prompt hashes, repetition
count, timeout, and planned commands.

Clean fixture:

```sh
python3 bench/ablation.py --dry-run --out bench/results/clean \
  --fixture bench/fixtures/ablation/spec-clean.md \
  --defects bench/fixtures/ablation/defects-clean.json \
  --arm current=bench/features/ablation/baseline.json
```

A clean fixture has no seeded defects. Recall is shown as `n/a`; precision is
1.0 when the arm reports no findings and 0.0 when it reports any. That measures
false-positive discipline, not recall.

Self-check, no model call:

```sh
python3 bench/ablation.py --self-check
```

It scores `sample-findings.json` and prints recall, precision, true positives,
false positives, false blockers, false majors, false nits, tokens, and wall
time. The sample carries expected values, so a scoring regression exits
non-zero.

Rescore a saved run after a scoring-rule change, with no model call:

```sh
python3 bench/ablation.py --rescore \
  --out path/to/saved-run \
  --defects bench/fixtures/ablation/defects-b.json
```

It reads `runs.csv` and each `runs/<arm>-r<rep>/findings.json`, writes
`runs-rescored.csv`, and prints the same aggregate, per-run, and spread tables.

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

False positives are also split by the finding's declared severity:
`false_blockers`, `false_majors`, and `false_nits`. Recall is reported by seeded
defect severity. A blocker-labeled finding that matches a seeded major is a true
positive, not a false blocker.

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

The four-arm pilot and its rejected improvement are archived in the brain.
Raw data stays in the ignored local results directory and is not shipped.

## Promotion rule

The canonical predeclared promotion rule is in
[`docs/benchmark-proof.md`](../docs/benchmark-proof.md).
The runner produces the metrics; it does not decide. A profile that wins recall
but loses precision or the false-blocker gate stays optional. Do not promote
from one fixture, and do not change the default without the rule's held-out
evidence.

## Limits

- Two synthetic specs and one model do not generalize. A clean no-defect fixture
  and a larger authored set are still missing.
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
- Aggregate means exclude rows with an `error`; failed rows remain in the
  per-run table and the Errors count. A no-JSON answer is now an error, not a
  zero-finding result.
- The runner does not replace Harbor, Terminal-Bench, hidden tests, or human
  review.
- The 2026-10-31 host smoke is one repetition on a different OpenCode version.
  It is not a quality claim. Do not cite a gain from this scaffold.

For the public benchmark protocol, see
[`docs/benchmark-proof.md`](../docs/benchmark-proof.md) and
[`docs/benchmark-tools.md`](../docs/benchmark-tools.md). The EGM research and
pilot reports are archived in the brain.
