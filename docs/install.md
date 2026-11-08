<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Install

LibreHarness can run as an OpenCode V2 plugin or as a copied runtime. The
plugin is the recommended path: commands, agents, and skills load from the
package, so package updates do not leave stale copies behind.

## Plugin install (recommended)

Add the package to the global `plugins` array in
`~/.config/opencode/opencode.json`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    {
      "package": "libreharness@1.1.0",
      "options": { "state": "~/.local/state/libreharness" }
    }
  ]
}
```

OpenCode loads the commands, agents, and skills from the package. Update by
changing the version or using a newer package; no runtime files are copied into
the config, so there is nothing to drift.

From a checkout, use the absolute path instead of the npm name:

```jsonc
{
  "package": "/path/to/libreharness",
  "options": { "state": "~/.local/state/libreharness" }
}
```

1.1.0 is prepared but not published yet. Until it is, use the checkout path
above, or the offline copy installer below.

## Offline copy install

The original one-command installer remains for machines that cannot load an npm
plugin:

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

From a checkout, use the same command directly:

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

For the plugin, change the package version in `plugins` and reload; no files
are copied. The commands below update an offline copy install.

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

- Linux only. macOS and Windows are not supported.
- Node 20 or newer.
- Python 3.10 or newer.
- Git and OpenCode 2.x.
- A model provider of your choice.

Jev is optional. The queue and quickstart work without a key.
