<!-- SPDX-License-Identifier: MIT -->

# Harbor adapter

Run LibreHarness as a custom Harbor agent:

```sh
uv tool install harbor==0.25.0
export OLLAMA_API_KEY=...
PYTHONPATH="$PWD" harbor run \
  -d terminal-bench@2.0 \
  -a harbor_agent.opencode_agent:OpenCodeLibreHarness \
  -m ollama-cloud/deepseek-v4.1-flash \
  --base-url https://ollama.com/v1 \
  --api-key-name OLLAMA_API_KEY \
  --api-format openai_chat_completions \
  --ak version=1.19.5
```

The plain baseline uses Harbor's stock OpenCode agent:

```sh
PYTHONPATH="$PWD" harbor run \
  -d terminal-bench@2.0 \
  -a opencode \
  -m <provider>/<model> \
  --ak version=1.19.5
```

Pins for a publishable run: Harbor 0.25.0 and OpenCode 1.19.5. Record both in
the run manifest. A different Harbor or OpenCode version needs a fresh smoke
and an update to the source-contract test.

## What the adapter changes

It inherits Harbor's stock OpenCode install and `run()` loop. It adds only:

1. `setup()` uploads `AGENTS.md`, `agents/`, `commands/`, `skills/`, and
   `bin/tasks.py` into `~/.config/opencode`, then chowns them to the agent user.
   `setup()` is the hook Harbor 0.25.0 actually calls; the earlier `configure()`
   hook was dead code, so the pilot did not upload the harness.
2. `exec_as_agent()` rewrites the final OpenCode command. Harbor's stock
   `run()` pipes the JSON stream through `stdbuf -oL tee`. OpenCode 1.19.5 can
   emit a benign EPIPE on a secondary stream and still exit non-zero after a
   completed run, so the pipeline makes a passing task look like
   `NonZeroAgentExitCodeError`. The rewrite writes the stream directly to the
   same log and tolerates only this case: non-zero exit, a completed
   `step_finish` with `reason: "stop"`, and `EPIPE` anywhere in the stream. A
   real crash still exits non-zero and raises through Harbor.
3. The model connection maps Ollama Cloud to `OLLAMA_API_KEY` and accepts
   `OPENCODE_API_KEY` and `OPENAI_API_KEY` as fallbacks.

It deliberately does not upload the local UI plugins, so auto-intake, close
reminders, and goal-watch cannot change a benchmark run.

## Profiles

An optional profile overlay is applied after the base runtime:

```sh
PYTHONPATH="$PWD" harbor run \
  -d terminal-bench@2.0 \
  -a harbor_agent.opencode_agent:OpenCodeLibreHarness \
  -m ollama-cloud/deepseek-v4.1-flash \
  --base-url https://ollama.com/v1 \
  --api-key-name OLLAMA_API_KEY \
  --api-format openai_chat_completions \
  --ak version=1.19.5 \
  --ak profile=egm
```

`profile` loads `profiles/<name>/` from the LibreHarness checkout, or from
`LIBREHARNESS_PROFILE`. The base runtime is uploaded first, then the profile
adds `agents/`, `commands/`, and `skills/`. A profile `AGENTS.md` is appended to
the base file, not substituted for it. Names that collide with a base skill,
command, or agent are rejected. No profile means the base runtime only.

The adapter writes `profile.json` into the trial's agent logs with the profile
name, source path, and a SHA-256 per source file. That is the profile manifest
for the run; it records the profile source, including its `README.md` and
`NOTICE`, while the sandbox renames `NOTICE` to
`LIBREHARNESS-PROFILE-NOTICE`. `LIBREHARNESS_PROFILE` is the environment
fallback when `--ak profile=...` is not convenient; an explicit `profile=`
wins.

## Post-fix smoke

`2026-10-31__14-33-39`: `break-filter-js-from-html`, reward 1.0, no exception,
4m 14s, $0.0215. The trial log shows the overlay `mkdir`; the log still starts
with EPIPE, and the guard tolerated it because a completed stop event followed.

`2026-10-31__14-38-12`: stock plain OpenCode on the same task, reward 1.0, but
`NonZeroAgentExitCodeError` from the same EPIPE. One task and one repetition;
this proves the false failure is removed, not that the harness is better.

## Drift guard

`tests/test_harbor_adapter.py` has a source-contract test. It fails when
Harbor's stock `OpenCode.run()` no longer contains the `| stdbuf -oL tee`
pipeline or the `2>&1 </dev/null` shape the rewrite depends on. That failure
means the adapter must be revisited, not ignored. If Harbor fixes the EPIPE
path upstream, delete the rewrite and keep the overlay upload.

`LIBREHARNESS_HOME` can point at a checkout different from the repository that
contains this adapter.

The Docker sandbox does not inherit OpenCode's host auth store. Export the
provider key in the shell that launches Harbor, for example `OLLAMA_API_KEY`,
or pass a mode-600 env file with `--env-file`. Do not commit the key.

Run one task as a smoke before a full dataset. Confirm the trial log contains
the overlay `mkdir`/`chown` commands and that the trial has no exception.
