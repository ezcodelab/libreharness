<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Troubleshooting

Every entry names the symptom, the likely cause, and a next step. If a command
fails, record the exact command and output before changing anything.

## Manual environment check

Run `python3 "$HARNESS_HOME/bin/doctor.py"` first. If it fails or cannot run,
use these checks to diagnose the same environment:

```sh
python3 --version
node --version
git --version
python3 "$HARNESS_HOME/bin/tasks.py" --help
node --check "$HARNESS_HOME/plugins/auto-intake.js"
node --check "$HARNESS_HOME/plugins/close-reminder.js"
node --check "$HARNESS_HOME/plugins/goal-watch.js"
node --check "$HARNESS_HOME/plugins/security-guard.js"
python3 -m json.tool "$HARNESS_HOME/opencode.json" >/dev/null
test -w "$HARNESS_STATE" && echo "state writable"
case "$HARNESS_STATE" in "$HARNESS_HOME"*) echo "WARNING: state is inside the checkout";; esac
test -n "${JEV_MODEL:-}" && echo "Jev model set" || echo "Jev not configured"
```

A missing helper is not a passed check. Record it.

## Install

### `python3: command not found`

Install Python 3.10 or newer, then confirm:

```sh
python3 --version
```

On a system where the interpreter is `python3.12`, put it on `PATH` as
`python3`, or create a small alias or wrapper. The bundled commands call
`python3` directly.

### `Permission denied` when running `bin/tasks.py`

Run it through the interpreter:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" ready
```

The file does not need the executable bit for this. Do not `chmod 777` it.

### The clone overwrote or conflicts with an existing config

Restore your backup, then install into a temporary directory and copy only the
files you need. Never overwrite `opencode.json`, `.env`, or a state directory.

### `opencode` does not see the harness

Check that `HARNESS_HOME` points at the checkout and that OpenCode is reading
the same config directory:

```sh
printf '%s\n' "$HARNESS_HOME"
ls "$HARNESS_HOME/commands" "$HARNESS_HOME/skills" "$HARNESS_HOME/plugins"
```

If `HARNESS_HOME` is not `~/.config/opencode`, copy or symlink `agents/`,
`commands/`, `skills/`, and `plugins/` into `~/.config/opencode/`. Restart
OpenCode after a change.

## Commands or skills do not appear

- Confirm the files are in the directory OpenCode reads. Global commands and
  skills live under the config directory, not under an arbitrary checkout.
- Confirm the command file has frontmatter with a `description`.
- Confirm a skill is a directory with `SKILL.md`, not a loose Markdown file.
- Restart OpenCode. A command or skill added at runtime may not be discovered
  until restart.
- Check the OpenCode version. The harness targets 2.x.
- Look for a parse error in the OpenCode log. A malformed frontmatter block can
  hide the whole command.

## Plugin load

### A local plugin does not run

Local plugins are loaded from `~/.config/opencode/plugins/` or a project's
`.opencode/plugins/`, not from an arbitrary path. If `HARNESS_HOME` is elsewhere,
copy or symlink the four files into the global plugin directory.

Check syntax:

```sh
node --check "$HARNESS_HOME/plugins/auto-intake.js"
```

Check the OpenCode version and the plugin API. The bundled plugins target the
hook shape in OpenCode 2.x. An older or newer host may not expose the same hooks.

The plugins fail open by design. A broken plugin usually produces no task, no
reminder, or no warning, rather than an error. Check the plugin file, the
environment, and the OpenCode log.

### `auto-intake` creates no task

- Is `AUTO_INTAKE=off` set?
- Is the prompt shorter than 12 characters, a question, a slash command, or a
  continuation word?
- Does the prompt match a secret pattern?
- Is `HARNESS_STATE` writable?
- Does `$HARNESS_HOME/bin/tasks.py` exist?
- Has this session already created a task? The plugin creates at most one per
  session.

Test the helper directly:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" new "Test intake" --status inbox
```

### `goal-watch` does not continue a goal

- Is the goal `active` with `autorun: true`?
- Does the goal's `session` match the idle session?
- Is more than one autorun goal active? The watcher refuses to choose.
- Has the goal reached `max_continuations`?
- Is the queue readable at `GOAL_WATCH_ROOT` or `HARNESS_STATE`?

The watcher never creates work and never marks a task done. It only nudges.

### `close-reminder` does nothing

- Is `CLOSE_REMINDER_MODE=off`?
- Has the session done real tool work? It needs a mutating tool or at least
  three tool calls.
- Has 30 minutes of idle time passed? Change `CLOSE_REMINDER_MS` to test.
- On macOS, `notify-send` is not used, so `notify` mode is silent. Use `prompt`
  mode or a platform notifier.
- The reminder is once per session.

## State and permissions

### `Permission denied` on the state root

```sh
mkdir -p "$HARNESS_STATE"
chmod 700 "$HARNESS_STATE"
```

Check that the current user owns it. Do not run the queue as root to work around
a permission problem.

### State is inside the checkout

If `HARNESS_STATE` is unset, `bin/tasks.py` currently falls back to the checkout
root. The plugins fall back to `$HOME/.local/state/libreharness`. That
mismatch can put tasks in the code tree and make every component disagree.

Always export `HARNESS_STATE`:

```sh
export HARNESS_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/libreharness"
```

Move existing `work/` and `metrics/` directories out of the checkout after
backing them up. Do not commit them.

### The lock is stuck

The lock is an advisory `flock` on `work/.lock`. It is released when the
process exits. If a process is still running, wait or stop it. Do not delete the
lock file while a writer is active. If no process is running, a stale lock file
is harmless; the next writer acquires it.

### Two tasks claim the same branch or worktree

The claim command rejects a branch or worktree already owned by an active or
review task. Use a different lane name or remove the old lane after it is
merged. Do not edit the task frontmatter to bypass the check.

## Queue errors

### `error: no task matching '<id>'`

The id or prefix does not match a task file. Run:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" list
```

### `error: ambiguous task prefix`

The prefix matches more than one task. Use more characters or the full id.

### `error: done needs real evidence`

Use a command and result, a measured check, or `[T]` with a plan. Placeholders
such as `none`, `ok`, `pass`, `done`, and `tests pass` are rejected.

### `error: open dependencies`

Finish the dependency or record an explicit risk acceptance and use `--force`.
Do not silently remove the dependency from the file.

### `error: ... is active; claim only ready/inbox/blocked`

The task is already claimed or in review. If it is yours, continue. If another
owner has it, stop and ask before dual-writing.

### `error: a goal needs at least one child task`

Create at least one child before closing a goal. A goal with no children is not
a complete umbrella.

### `error: goal has open children`

Close or abandon every child before closing the goal. The error lists the open
ids.

## Jev

### `no Jev key` and exit 3

Set one key source:

```sh
export JEV_KEY_FILE="$HOME/.config/opencode/jev.key"
chmod 600 "$JEV_KEY_FILE"
```

or:

```sh
export JEV_API_KEY="<key>"
```

The rc.1 error text mentions `console.key`; the resolver reads `jev.key`,
`JEV_KEY_FILE`, `JEV_API_KEY`, `OPENCODE_API_KEY`, and `TYPESAFE_API_KEY`. Use
the documented names.

At the workflow level, exit 3 is a skip. `/review` and `/close` continue without
Jev. That is expected.

### `error: set JEV_MODEL or pass --model`

No model is configured. The client does not hardcode one. Set `JEV_MODEL` to a
model your endpoint offers, or pass `--model`.

### `FREE JEV GONE` and exit 4

The requested model is no longer offered. Do not silently switch to a paid
model. Choose a current model, update `JEV_MODEL`, and re-run `--check`.
Record the change in the task or review note.

### HTTP 403 from Cloudflare (Error 1010)

The client signature was blocked, not necessarily the key. The reference client
sends `curl/8.0` as its user agent. If the error persists, check the endpoint,
the network, and the key file. A 403 without Error 1010 usually means the key
lacks permission for the call.

### HTTP 401 or 403 from the service

Check:

- the key is current and not truncated;
- the key has the permission the endpoint needs;
- the endpoint URL is correct;
- the key is not being sent to a different host than you expect.

### `the diff looks like it contains a secret or PII`

Redact the diff or task. Do not pass `--allow-secret-shaped` unless a person has
reviewed the input and accepts the egress. The guard is a pattern match; a
redaction can still miss something.

### `Jev unreachable` or a timeout

Check the endpoint and network. Increase `--timeout` only if the service is slow,
not if it is down. A failed advisory call should not block the task; the
workflow treats exit 3 as unavailable.

### `--mock` still asks for a model

That is expected. The client validates `JEV_MODEL` before it enters the mock
branch. Set any non-empty value, for example `JEV_MODEL=example-model`.

### The triage client has no mock

Correct for rc.1. Only review and plan have `--mock`; triage does not. Test the
triage parser with a fixture instead of a live call.

## Upgrade and rollback

- Read the changelog before checking out a tag.
- Back up `HARNESS_STATE` before a major release or a state migration.
- Run the environment check after the checkout.
- Restart OpenCode.
- If a rollback crosses a migration, restore the backup. Do not run an old
  binary against a newer state layout.

## Windows

1.0.0 does not support Windows. `bin/tasks.py` imports `fcntl`, so it fails on a
native Windows Python. WSL2 provides a Linux environment and may work, but it is
not tested for 1.0.0. The 1.1 preview is planned to put the lock behind a
cross-platform module. Until then, use Linux or macOS.

## Documentation checks

If a relative link fails:

```sh
python3 bin/docs_lint.py . --skills-dir skills
```

The lint prints the file, line, and missing target. Fix the link or add the
file. External links are not checked offline.

## Next

- [FAQ](faq.md)
- [Install](install.md)
- [Jev](jev.md)
