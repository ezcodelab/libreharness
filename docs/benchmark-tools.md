<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Benchmark tool review

Status: **research complete, 2026-10-30. No benchmark run yet.**

Question: is there already a tool for benchmarking an OpenCode-based coding
harness, so LibreHarness does not invent a private benchmark?

Answer: **yes. Use Harbor with Terminal-Bench 2.0 for the headline.** Keep the
small B1-B8 suite only as a LibreHarness workflow supplement, not as the public
comparison.

## Recommendation

| Choice | Why |
|---|---|
| **Harbor + Terminal-Bench 2.0** | Official Terminal-Bench harness, pre-integrated OpenCode agent, Docker tasks, resolution rate, token and cost reporting, public leaderboard |
| SWE-bench Verified or Lite via Harbor | Recognized code-patch benchmark, but heavier and not harness-workflow specific; use as a secondary result |
| `anomalyco/opencode-bench` | Real repositories and OpenCode support, but LLM-judge scoring, no deterministic hidden tests, and no license metadata |
| `opencode-agent-evaluator` | Useful OpenCode token tracing on Phoenix/Chimera, but a small synthetic suite with no public standard |
| `coding-agent-eval-harness` | Agent adapters and a composite score, but not a recognized public benchmark |
| Local B1-B8 suite | Keep for fast harness regression only; do not publish its score as the headline |

## Evidence

### Harbor and Terminal-Bench

- Harbor is from the creators of Terminal-Bench and is the official harness for
  Terminal-Bench 2.0: <https://github.com/harbor-framework/harbor>.
- Harbor is Apache-2.0, actively maintained, and its agent list includes
  `opencode`: <https://github.com/harbor-framework/harbor/blob/main/docs-mintlify/agents/pre-integrated-agents.mdx>.
- The OpenCode integration reads `opencode run --format=json`, supports skills,
  MCP, model variants, and an `opencode_config` overlay:
  <https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/opencode.py>.
- Terminal-Bench measures **resolution rate**: tasks whose verifier passes
  divided by tasks run. The public board is at <https://www.tbench.ai/>.
- The Terminal-Bench 2.0 board includes an OpenCode entry at 51.7% with Claude
  Opus 4.5, so there is an external reference point:
  <https://www.tbench.ai/?version=2.0>.
- The 2026 scaffold-effect study uses Harbor to compare Goose, OpenCode, and
  OpenHands-SDK on Terminal-Bench Pro and recommends reporting harness-model
  pairs with pass rate, tokens per solved task, latency, and failure
  fingerprints: <https://arxiv.org/abs/2607.22585>.
- The 2026 harness-effects study uses OpenCode on SWE-bench Pro, ProgramBench,
  and GitTaskBench, reinforcing that the harness is a variable worth measuring:
  <https://arxiv.org/html/2609.32459v1>.

### Why not make SWE-bench the headline

- SWE-bench is the recognized patch-generation benchmark, and Harbor can adapt
  it. It is heavy: Docker per instance, hundreds of tasks, and patch grading:
  <https://github.com/SWE-bench/SWE-bench>.
- 2026 work documents contamination and patch-size limitations. It is useful as
  a secondary result, not the only harness comparison:
  <https://arxiv.org/abs/2602.02262>.
- Terminal-Bench is closer to the harness question: terminal tasks, environment
  setup, iterative debugging, and agent loops.

### Why not `opencode-bench`

- Repository: <https://github.com/anomalyco/opencode-bench>.
- It supports OpenCode and real production commits, but scores with three LLM
  judges across five dimensions. It is a quality-judgment benchmark, not a
  deterministic resolution rate.
- No license metadata was reported by the GitHub API at review time; the last
  push was 2026-03-13. Do not make it the public headline.

### Why not `opencode-agent-evaluator`

- Repository: <https://github.com/DasDigitaleMomentum/opencode-agent-evaluator>.
- It runs OpenCode agents on Phoenix and Chimera and reports token usage. It is
  useful for debugging harness cost, but the fixtures are synthetic and there is
  no public standardized leaderboard.

## Standard metric

Use **Terminal-Bench 2.0 resolution rate** as the headline:

```text
resolution rate = tasks whose verifier passes / tasks run x 100
```

Report alongside it:

- median tokens per solved task;
- median wall time per task;
- median cost per task;
- model, provider, OpenCode version, harness commit, task dataset version;
- number of attempts and confidence interval.

Do not blend these into a composite score.

The **before** baseline is plain OpenCode on the same dataset, same model, and
same environment. The **after** result is OpenCode with LibreHarness installed
in the same task environment. Both use the same Harbor version and task hashes.

## Integration gap

Harbor's `opencode` agent supports skills and an `opencode_config` overlay, but
it does not install the full LibreHarness runtime (queue, commands, plugins,
`AGENTS.md`) automatically. To benchmark the complete harness:

1. Create a Harbour agent adapter `opencode-libreharness` that installs the
   LibreHarness release candidate in the sandbox and points OpenCode at it.
2. Or bake the harness into the Terminal-Bench task image and keep the stock
   `opencode` agent. This is simpler but couples the image to the harness.
3. Keep the plain arm on stock `opencode`, with no harness files.

The adapter is the cleaner comparison and should be the next implementation
task.

## Commands to validate

```sh
uv tool install harbor
harbor datasets list
harbor run -d terminal-bench@2.0 -a opencode -m <provider>/<model> --n-attempts 1
```

The model must be available to the OpenCode agent inside the sandbox. For
Ollama Cloud, configure the provider through `opencode_config` or the Harbor
agent auth resolution. No live run was made in this review.

## Decision

Adopt Harbor + Terminal-Bench 2.0. Retire the custom five-hundred-task ambition
and the private B1-B8 suite as the headline. The local B1-B8 suite may remain a
fast smoke test, but its score is not comparable to public agent results.

Sources were checked on 2026-10-30. Re-check the Harbor release, Terminal-Bench
version, and OpenCode adapter before publishing a score.
