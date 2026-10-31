<!-- SPDX-License-Identifier: MIT -->

# Harbor adapter

Run LibreHarness as a custom Harbor agent:

```sh
uv tool install harbor
export OLLAMA_API_KEY=...
PYTHONPATH="$PWD" harbor run \
  -d terminal-bench@2.0 \
  -a harbor_agent.opencode_agent:OpenCodeLibreHarness \
  -m ollama-cloud/deepseek-v4.1-flash \
  --base-url https://ollama.com/v1 \
  --api-key-name OLLAMA_API_KEY \
  --api-format openai_chat_completions
```

The plain baseline uses Harbor's stock OpenCode agent:

```sh
PYTHONPATH="$PWD" harbor run \
  -d terminal-bench@2.0 \
  -a opencode \
  -m <provider>/<model>
```

The adapter uploads `AGENTS.md`, `agents/`, `commands/`, `skills/`, and
`bin/tasks.py` into the sandbox's `~/.config/opencode`. It deliberately does
not upload the local UI plugins, so auto-intake, close reminders, and
goal-watch cannot change a benchmark run.

`LIBREHARNESS_HOME` can point at a checkout different from the repository that
contains this adapter. The model is authenticated by Harbor's stock OpenCode
integration.

The Docker sandbox does not inherit OpenCode's host auth store. Export the
provider key in the shell that launches Harbor, for example
`OLLAMA_API_KEY`, or pass a mode-600 env file with `--env-file`. Do not commit
the key.

The adapter has not yet been exercised against a live Terminal-Bench task.
Validate with a one-task smoke run before starting a full dataset.
