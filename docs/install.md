<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Install

LibreHarness installs with one command into the OpenCode config directory.

## One command

```sh
npx libreharness init
```

The installer asks for two paths, then copies the runtime, creates the state
directory, and runs `bin/doctor.py`:

```text
Install into [~/.config/opencode]:
State directory [~/.local/state/libreharness]:
```

For scripts or CI, skip the prompts:

```sh
npx libreharness init --yes
```

The release candidate is not published to npm yet. From a checkout, use the
same command directly:

```sh
node bin/libreharness.js init
node bin/libreharness.js init --yes
```

## What it installs

- `AGENTS.md`, `agents/`, `commands/`, `skills/`, `plugins/`, and `bin/`
- `opencode.json` from the example, only when none exists
- `LICENSE`, `NOTICE`, `opencode.example.json`, and the runtime docs
- `$HARNESS_STATE`, created with mode 700

It never copies state, tests, benchmark data, credentials, or private files.
It does not choose a provider or model.

## Options

| Option | Meaning |
|---|---|
| `--home <dir>` | OpenCode config directory; default `~/.config/opencode` |
| `--state <dir>` | Runtime state directory; default `~/.local/state/libreharness` |
| `--yes` | Use the defaults, skip prompts |
| `--dry-run` | Print the plan without writing |
| `--force` | Replace conflicting files after backing them up |
| `--help`, `--version` | Show help or the version |

A normal second run is safe. Existing files are kept and reported. If a file
differs, `--force` moves the existing copy to
`~/.config/opencode/.libreharness-backup-<timestamp>/` before replacing it.

## Choose a model

The example config deliberately has no model ID. Start OpenCode, connect a
provider, and choose a model with `/models`. The harness roles and cost policy
are in [model-routing.md](model-routing.md).

## Upgrade

From a checkout:

```sh
git pull
node bin/libreharness.js init --force
```

From npm, after publication:

```sh
npx libreharness@latest init --force
```

`--force` backs up every file it replaces. Review the backup before deleting
it. State under `$HARNESS_STATE` is not touched by an upgrade.

## Manual path

Use this only if the installer cannot run. It is the same layout the installer
creates.

```sh
export HARNESS_HOME="$HOME/.config/opencode"
export HARNESS_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/libreharness"
git clone <repository-url> "$HARNESS_HOME"
cp "$HARNESS_HOME/opencode.example.json" "$HARNESS_HOME/opencode.json"
mkdir -p "$HARNESS_STATE"
chmod 700 "$HARNESS_STATE"
python3 "$HARNESS_HOME/bin/doctor.py"
```

If `$HARNESS_HOME` already exists, back it up first and merge by hand. Never
delete an existing OpenCode config.

## Requirements

- Linux or macOS. Windows is a 1.1 preview.
- Node 20 or newer.
- Python 3.10 or newer.
- Git and OpenCode 2.x.
- A model provider of your choice.

Jev is optional. The queue and quickstart work without a key.
