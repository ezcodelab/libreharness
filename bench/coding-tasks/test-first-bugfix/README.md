<!-- SPDX-License-Identifier: MIT -->
# Test-first bugfix task

A local Harbor task that requires the agent to add a regression test before
fixing a zero-division bug.

## What it checks

- `/app/tests/test_regression.py` exists and expects `ValueError`;
- the existing `/app/tests/test_calc.py` is unchanged;
- the new test fails against the baseline code;
- the fixed code passes the new test and the existing test;
- `safe_div(1, 0)` raises `ValueError`.

The verifier runs in the task environment (`environment_mode = "shared"`)
because it reads `/app`.

## Run

```sh
PYTHONPATH="$PWD" harbor run \
  -p bench/coding-tasks/test-first-bugfix \
  -a harbor_agent.opencode_agent:OpenCodeLibreHarness \
  -m ollama-cloud/deepseek-v4.1-flash \
  --base-url https://ollama.com/v1 \
  --api-key-name OLLAMA_API_KEY \
  --api-format openai_chat_completions \
  --ak version=1.19.5 \
  --ak profile=egm \
  -k 1
```

This task is separate from the Terminal-Bench suite. It exists because the
Terminal-Bench tasks do not require the agent to author a test.
