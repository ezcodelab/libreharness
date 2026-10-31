<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Install

This guide installs the harness on Linux or macOS. Windows is not supported in
1.0.0.

The install has not been verified on a clean machine for this release
candidate. Treat the steps as a checklist, not as a tested claim. If a command
fails, record the exact command and output in your task rather than skipping
it.

## Prerequisites

| Requirement | Why |
|---|---|
| Linux or macOS | The queue uses POSIX `fcntl` locking |
| Git | Clone, tags, worktrees, and lane review |
| Python 3.10 or newer | The queue and Jev clients are stdlib Python |
| Node 20 or newer | Plugin checks, plugin tests, and optional example plugins |
| OpenCode 2.x | Loads agents, commands, skills, and local plugins |
| A model provider | OpenCode needs a model; the harness does not choose one for you |

Optional: a Jev endpoint and key. The queue and quickstart work without them.

## Choose two roots

The harness separates code from state:

| Variable | Default in documentation | Holds |
|---|---|---|
| `HARNESS_HOME` | `$HOME/.config/opencode` | Code, agents, commands, skills, plugins, and configuration |
| `HARNESS_STATE` | `$HOME/.local/state/libreharness` | Tasks, board, lock, metrics, and optional Jev key file |

The recommended install puts the checkout at the OpenCode global config
directory, because OpenCode automatically discovers `agents/`, `commands/`,
`skills/`, and `plugins/` there. If you keep the checkout somewhere else,
OpenCode will not discover those directories by itself. Copy or symlink the
four directories into the config directory, and keep `HARNESS_HOME` pointing at
the checkout.

Do not put `HARNESS_STATE` inside `HARNESS_HOME`. Runtime data should not be
committed, scanned as source, or removed by a checkout update.

## Back up first

If `$HOME/.config/opencode` already exists, back it up and review the diff
before copying anything into it:

```sh
cp -a "$HOME/.config/opencode" "$HOME/.config/opencode.backup-$(date +%Y%m%d)"
```

Do not overwrite an existing `opencode.json`, `.env`, or state directory. The
example config is a starting point, not a replacement for your provider
configuration.

## Get the checkout

```sh
export HARNESS_HOME="$HOME/.config/opencode"
git clone <repository-url> "$HARNESS_HOME"
```

If `$HARNESS_HOME` already exists, clone into a temporary directory, review the
tracked files, and copy only what you need. Never use a command that deletes
the existing directory.

If you are installing from a local archive instead of a clone, copy the tracked
files into `$HARNESS_HOME` and keep the same layout.

## Copy the example config

```sh
cp "$HARNESS_HOME/opencode.example.json" "$HARNESS_HOME/opencode.json"
```

The example config:

- has no model ID and no API key;
- enables the `todowrite` tool and the shell tool;
- includes an optional remote `grep-app` MCP server;
- has an empty external plugin list.

The shell permission is broad. It is convenient for a local trial and too
broad for sensitive or production work. Narrow `permissions` before you use
the harness on a repository with credentials, customer data, or deploy access.
Remove the `grep-app` MCP entry if you do not want that remote service.

## Choose a provider and model

OpenCode needs a provider and a model. The harness does not hardcode either.

Use OpenCode's normal provider login or model picker, or add a `model` field to
`opencode.json`. The value is provider-specific. A model ID that appears in an
example plugin is an example, not a recommendation or a default.

The core configuration is provider-agnostic. Roles and cost policy are
described in [model-routing.md](model-routing.md).

## Set the state root

```sh
export HARNESS_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/libreharness"
mkdir -p "$HARNESS_STATE"
chmod 700 "$HARNESS_STATE"
```

Add both exports to your shell profile if you want them in every session:

```sh
export HARNESS_HOME="$HOME/.config/opencode"
export HARNESS_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/libreharness"
```

Always set `HARNESS_STATE` explicitly. The plugins fall back to
`$HOME/.local/state/libreharness` when it is unset. `bin/tasks.py` currently
falls back to the checkout root when it is unset, which would put runtime data
inside the code tree. The explicit export keeps every component on the same
root.

If your umask is permissive, set `umask 077` before creating the state root, or
run `chmod 700` on it. Task files are not encrypted. Use full disk encryption
if the state contains sensitive work.

## Run the environment check

```sh
python3 "$HARNESS_HOME/bin/doctor.py"
```

`bin/doctor.py` is a read-only check of the Python and Node versions, Git,
writable state, state outside the checkout, obvious secrets in
`opencode.json`, `node --check` on the local plugins, `tasks.py --help`, and
whether Jev is configured. It never calls a model. If it fails, use the manual
checks in
[troubleshooting.md](troubleshooting.md#manual-environment-check) and fix the
reported item before starting OpenCode.

## Start OpenCode

From a project directory:

```sh
opencode
```

Then check that the harness is loaded:

```text
/queue
```

A fresh state root prints `no tasks` and writes a board when you create the
first task. If OpenCode does not see the commands, see
[troubleshooting.md](troubleshooting.md#commands-or-skills-do-not-appear).

## First task

Follow [quickstart.md](quickstart.md). It uses a temporary state root and does
not need a Jev key.

## Upgrade

1. Read [CHANGELOG.md](../CHANGELOG.md) and the target tag.
2. Back up `HARNESS_STATE`.
3. Fetch tags and check out the target:

```sh
git -C "$HARNESS_HOME" fetch --tags
git -C "$HARNESS_HOME" checkout vX.Y.Z
```

4. Run the environment check again.
5. Restart OpenCode.

State under `HARNESS_STATE` is preserved across patch and minor releases. A
major release that changes the state layout must ship a migration script and a
backup step. If it does not, stop.

If you installed by copying files instead of a clone, copy the new tracked
files over the old ones without deleting `opencode.json`, `.env`, or state.

## Rollback

```sh
git -C "$HARNESS_HOME" checkout vPREVIOUS
```

Restart OpenCode. State is preserved. If the rollback crosses a state migration,
restore the backup you made before the upgrade. Do not run a newer queue against
an older migrated state without checking the changelog.

## Uninstall

1. Remove the harness checkout or the copied files from `$HARNESS_HOME`.
2. Remove the `opencode.json` entries you added, or restore your backup.
3. Decide what to do with `HARNESS_STATE`. Back it up before deleting it if it
   contains work you may need.

```sh
# Back up state first.
cp -a "$HARNESS_STATE" "$HOME/libreharness-state-backup"
# Then remove it only if you are sure.
rm -rf "$HARNESS_STATE"
```

Do not delete a state root that another profile or user still uses.

## Multiple profiles

1.0.0 does not have a first-class profile command. The supported approach is
one checkout and one state root per profile, selected with environment
variables:

```sh
export HARNESS_HOME="$HOME/.config/opencode-work"
export HARNESS_STATE="$HOME/.local/state/libreharness-work"
```

OpenCode itself still reads its own configuration directory. If you need fully
separate OpenCode configurations, use separate `HOME` or `XDG_CONFIG_HOME`
values for each profile, and set `HARNESS_HOME` and `HARNESS_STATE` in each
environment. Do not share one state root between users; the lock protects
concurrent writers, not confidentiality.

## Next

- [Quickstart](quickstart.md)
- [Concepts](concepts.md)
- [Security and privacy](security-privacy.md)
