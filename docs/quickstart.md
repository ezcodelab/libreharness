<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Quickstart

## 1. Install

```sh
npx libreharness init
```

The guided installer asks for the OpenCode config directory and state directory,
then runs the environment check. For an unattended install:

```sh
npx libreharness init --yes
```

From a checkout, use `node bin/libreharness.js init`.

## 2. Start OpenCode

Open OpenCode in your project and choose a provider and model with `/models`.
The installer does not choose either for you.

## 3. Describe the outcome

Describe the change in OpenCode. Auto-intake creates one task, and the agent
runs brief, implement, verify, review, close, and ship. You do not need to type
a slash command.

## 4. Manual inspection and escape hatches

The CLI below creates and closes a task by hand. Use it to inspect the queue,
reproduce a problem, or intervene directly. Set the two roots once; they are the
same defaults the installer uses.

```sh
export HARNESS_HOME="${HARNESS_HOME:-$HOME/.config/opencode}"
export HARNESS_STATE="${HARNESS_STATE:-$HOME/.local/state/libreharness}"
ID=$(python3 "$HARNESS_HOME/bin/tasks.py" new "Try LibreHarness" \
  --project demo \
  --scope "Create and close one task." \
  --acceptance "- board lists the task")
python3 "$HARNESS_HOME/bin/tasks.py" claim "$ID" --owner quickstart
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" review --note "quickstart"
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" done \
  --evidence "python3 $HARNESS_HOME/bin/tasks.py board: task listed"
python3 "$HARNESS_HOME/bin/tasks.py" board
```

The evidence gate rejects `none`, `ok`, `pass`, and `tests pass`. Use a command
and result, a measured check, or an explicit `[T]` with a plan.

## 5. Use it from OpenCode

The normal path needs no command. `/goal`, `/brief`, `/review`, `/close`, and
the shipping flow remain escape hatches for a human who wants to intervene. The
harness loads the queue, skills, commands, agents, and local plugins from the
plugin package.

Optional Jev review without a key:

```sh
printf 'diff --git a/demo.txt b/demo.txt\n+hello\n' > "$HARNESS_STATE/demo.diff"
JEV_MODEL=example-model python3 "$HARNESS_HOME/bin/jev_review.py" \
  --mock good --diff "$HARNESS_STATE/demo.diff" --task "Quickstart"
```

## 6. Compare on Terminal-Bench

The standardized external benchmark is Terminal-Bench 2.0 through Harbor. Run
plain OpenCode first, then OpenCode with LibreHarness, using the same model and
environment:

```sh
uv tool install harbor
harbor run -d terminal-bench@2.0 -a opencode -m <provider>/<model>
```

The headline is **resolution rate**. Report tokens, wall time, and cost beside
it. See [benchmark-tools.md](benchmark-tools.md) and the
[benchmark proof protocol](benchmark-proof.md).

## Next

- [When to use what](when-to-use.md)
- [Install options](install.md)
- [Workflow](workflow.md)
- [Model routing](model-routing.md)
- [Benchmark code](../bench/README.md)
