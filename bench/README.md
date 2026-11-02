<!-- SPDX-License-Identifier: MIT -->
# Benchmark code

Status: **benchmark code only. No results are shipped.**
The public headline is Terminal-Bench 2.0 via Harbor; see
[`docs/benchmark-tools.md`](../docs/benchmark-tools.md) and the protocol in
[`docs/benchmark-proof.md`](../docs/benchmark-proof.md).

This directory contains the benchmark code for comparing the EGM and
Superpowers profiles with the LibreHarness base and stock OpenCode:

| Path | Purpose |
|---|---|
| `ablation.py` | Fast review-feature ablation and scoring |
| `ablation.md` | How the ablation works and how to add a prompt arm |
| `coding.py` | Fixed Terminal-Bench coding runner |
| `coding.md` | Coding metrics and test-first limits |
| `coding-suite.json` | Fixed hard-v2 tasks and five arms |
| `analyze.py` | Per-task summary and paired bootstrap |
| `features/ablation/` | Declarative review prompt arms |
| `fixtures/ablation/` | Seeded review specs and defect rules |
| `results/` | Generated run data, ignored except `.gitkeep` |

The Harbor adapter lives in [`harbor_agent/`](../harbor_agent/); the optional
profiles live in [`profiles/`](../profiles/).

## Review ablation

```sh
python3 bench/ablation.py --dry-run
python3 bench/ablation.py --self-check
python3 bench/ablation.py --live --model provider/model \
  --repetitions 3 --seed 0 --out bench/results/ablation
```

## Coding benchmark

```sh
python3 bench/coding.py --dry-run
python3 bench/coding.py --live --repetitions 3 --seed 0 \
  --out bench/results/coding
```

`--live` needs Harbor 0.25.0, OpenCode 1.19.5, and the provider key in the
environment. It writes one manifest and `runs.csv`; raw jobs stay under the
output directory.

## Data policy

- No API keys, tokens, auth headers, or personal paths in committed data.
- `jobs/` and `bench/results/*` are ignored. Raw session data stays private or
  is sanitized before publication.
- Publish `runs.csv`, the manifest, task hashes, and the analysis together, or
  do not publish a score.
- Report resolution, exceptions, cost, and wall time separately. No composite
  score.

## Claim policy

No performance or quality claim is made from this directory until the protocol
has been run and reviewed. A neutral or negative result is published with the
same care as a positive one. Experiment reports and the old local suite are
archived outside the public tree.
