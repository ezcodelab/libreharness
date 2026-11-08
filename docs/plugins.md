<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Plugins

The harness ships four local OpenCode plugins and two opt-in example plugins.
Local plugins use Node built-ins only. None of them calls a model. For when to
keep each one on, see [When to use what](when-to-use.md).

In 1.1.0 the four are bundled into the main V2 server plugin. The standalone
files remain in the package for the offline copy install.

## How local plugins load

With the V2 plugin, the main server part imports the four after it sets
`HARNESS_HOME` and `HARNESS_STATE`; no copy or symlink is needed. The offline
copy install still loads them from the global plugin directory,
`~/.config/opencode/plugins/`, or a project's `.opencode/plugins/`.

External npm plugins are listed in the OpenCode configuration. The example
config has an empty list. The harness does not require or endorse any external
plugin.

A plugin must never block a session because of its own misconfiguration. The
bundled plugins catch their own errors, log at most a short warning, and
continue.

## Bundled plugins

| Plugin | Use when | What it does | Disable | Failure mode |
|---|---|---|---|---|
| `auto-intake` | A nontrivial prompt should become an inbox task without retyping | Creates an inbox task from a nontrivial prompt before the model answers | `AUTO_INTAKE=off` | No task is created; the prompt continues |
| `close-reminder` | A long session should remind you to close finished work | Sends one desktop notification or prompt after real tool work goes quiet | `CLOSE_REMINDER_MODE=off` | No notification; the next session still reminds |
| `goal-watch` | An active goal is closable, or an autorun goal should continue | Reminds once per session when a goal can close; continues one autorun goal with ready children | Do not load the plugin | No reminder or continuation; the goal stays active |
| `security-guard` | You want an advisory warning after a risky edit pattern | Appends one advisory warning after an edit matches a risky pattern | Do not load the plugin | No warning; the edit proceeds |

### auto-intake

Turns a prompt into an `inbox` task when the prompt looks like work. It is the
reason a user can type a request and later find a task without running
`/goal` first.

It skips:

- slash commands and `@` mentions;
- continuation words such as "continue" or "go on";
- delegation prompts such as "you are" or "act as";
- question-only prompts;
- prompts shorter than 12 characters;
- prompts that match its secret patterns;
- a session that already produced a task, so one prompt does not create a
  duplicate.

It redacts secret-shaped and PII-shaped text in the task title. If the prompt
matches its secret patterns, it does not create a task. The prompt still goes
to the model provider as usual; the guard prevents queue storage, not provider
egress.

| Variable | Default | Meaning |
|---|---|---|
| `AUTO_INTAKE` | on | Set to `off` to disable |
| `AUTO_INTAKE_ROOT` | `HARNESS_STATE` or `$HOME/.local/state/libreharness` | State root |
| `AUTO_INTAKE_TASKS` | `$HARNESS_HOME/bin/tasks.py` | Queue helper |
| `HARNESS_HOME` | `$HOME/.config/opencode` | Checkout |
| `HARNESS_STATE` | `$HOME/.local/state/libreharness` | State root |

Failure mode: if the helper is missing, the state root is not writable, or the
helper exits non-zero, the plugin catches the error and the prompt continues
without a task. That is intentional. A queue failure is not a reason to block
the session.

Test:

```sh
node tests/auto-intake.test.mjs
```

### close-reminder

Watches tool activity. After a session has done real work and then goes idle
for 30 minutes, it sends one reminder. "Real work" means at least one mutating
tool, or at least three tool calls. It nudges once per session.

| Variable | Default | Meaning |
|---|---|---|
| `CLOSE_REMINDER_MODE` | `notify` | `notify`, `prompt`, or `off` |
| `CLOSE_REMINDER_MS` | `1800000` | Idle time in milliseconds |

`notify` uses `notify-send` on Linux. Without a notification daemon it silently
does nothing. `prompt` sends a message into the session and costs model tokens.
`off` disables the plugin.

Failure mode: no `notify-send`, no desktop session, or a closing session means
the reminder is missed. That is safe. There is no retry queue.

Test: there is no dedicated unit test in 1.0.0. Check syntax with:

```sh
node --check plugins/close-reminder.js
```

### goal-watch

Watches `session.idle` for two jobs.

**Closable reminder.** If any active goal has all children final, it sends one
reminder per goal per session, including goals created by another session. The
reminder says the goal is ready to close and asks the operator to reply
"close now" to run `/close <goal>`, or "later" to keep it open. It never closes
the goal, marks it done, or repeats the reminder in the same session. The prompt
tells an unrelated session to ignore it.

**Continuation.** It also nudges one active goal with `autorun: true` and ready
children, provided the goal's `session` field matches the idle session. It
refuses to continue when more than one autorun goal matches and uses the goal's
`max_continuations` budget.

A missing queue, malformed JSON, or a closing session is a no-op, not a crash.

| Variable | Default | Meaning |
|---|---|---|
| `GOAL_WATCH_ROOT` | `HARNESS_STATE` or `$HOME/.local/state/libreharness` | State root |
| `GOAL_WATCH_TASKS` | `$HARNESS_HOME/bin/tasks.py` | Queue helper |
| `HARNESS_HOME` | `$HOME/.config/opencode` | Checkout |
| `HARNESS_STATE` | `$HOME/.local/state/libreharness` | State root |

To disable it, do not load the file: remove or rename it in the plugin
directory. There is no `GOAL_WATCH=off` switch in this version.

Test:

```sh
node tests/goal-watch.test.mjs
```

### security-guard

Scans edit, write, patch, and apply_patch input after the tool runs. It appends
one warning listing the matched rules. It never blocks the tool, calls a model,
or uses the network.

Rules:

| Id | Pattern |
|---|---|
| `yaml-unsafe-load` | `yaml.load` or `yaml.unsafe_load` |
| `pickle-load` | `pickle.load` or `pickle.loads` |
| `torch-load` | `torch.load` without `weights_only=True` |
| `html-assignment` | `innerHTML` or `outerHTML` assignment |
| `child-process-exec` | `child_process.exec` or `execSync` |
| `actions-injection` | untrusted `github.event` data in a workflow `run:` |

To allow a known use, add a comment to the edit:

```text
security-guard: allow pickle-load because the input is a trusted local fixture
```

A comment with no rule id allows all matches in that edit. Use the rule id when
you can.

Failure mode: a scan failure is swallowed and the tool result is unchanged.
There is no environment switch in 1.0.0. Disable by not loading the plugin.

Test:

```sh
node tests/security-guard.test.mjs
```

## Writing a plugin

1. Use ESM and Node built-ins.
2. Export an object with an `id` and a `setup(ctx)` function.
3. Register only the hooks you need. Clean them up on shutdown.
4. Catch your own errors. Never throw out of a hook.
5. Read code from `HARNESS_HOME` and state from `HARNESS_STATE`.
6. Add a disable switch and document it.
7. Add a test that does not need a model or network.
8. Run `node --check <file>`.

Do not put a provider key in a plugin. Do not spawn a shell with interpolated
user text. Use `execFile` with an argument array and a timeout, as the bundled
plugins do.

## Next

- [Model routing](model-routing.md)
- [Security and privacy](security-privacy.md)
- [Troubleshooting](troubleshooting.md)
