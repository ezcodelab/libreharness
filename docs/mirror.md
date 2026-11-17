<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Public mirror

Gitea is canonical. GitHub is a read-only public mirror for **Credarr** and
**LibreHarness** only. Other repositories stay on Gitea.

The mirror copies:

- Gitea `main` to GitHub `main`
- Gitea tags to GitHub tags

It never copies internal branches, never deletes GitHub branches or tags, and
never creates or deletes GitHub releases.

## Why not a Gitea push mirror

Gitea's push mirror uses `git push --mirror`. It prunes GitHub refs that are not
in Gitea, can delete release tags, and needs a token with `workflow` scope to
update `.github/workflows`. A failed sync is not atomic; tags can disappear
before a later ref is rejected.

This repository uses a local pull mirror instead.

## Run it

The job must run on a host that can reach both Gitea and GitHub, such as the NAS
runner. The checkout needs:

- `origin` pointing at Gitea
- `github` pointing at GitHub
- write access to GitHub, normally an SSH deploy key

Run once:

```sh
python3 bin/mirror_public.py \
  --repo /workspace/credarr \
  --repo /workspace/libreharness \
  --source origin --target github
```

Run continuously in a container:

```sh
python3 bin/mirror_public.py \
  --repo /workspace/credarr \
  --repo /workspace/libreharness \
  --source origin --target github --loop --interval 600
```

On a systemd host, install the units in `ops/systemd/` and enable
`libreharness-mirror.timer` and `libreharness-mirror-check.timer`. The mirror
holds `mirror.lock` for the whole run, so overlapping timers skip cleanly.

The mirror writes an atomic `mirror-status.json` with the last attempt, last
success, duration, and per-repo result. The check unit fails if the last
successful push is older than 20 minutes or the last run failed. Its `OnFailure`
alert unit writes a `user.err` journal entry; point that unit at your own email
or webhook if you need active notification.

The units under `ops/systemd/` target a Linux VM or runner with
`/opt/libreharness` and `/workspace`, and a `libreharness` system user. For a
user-level install, create these units in `~/.config/systemd/user/`:

- `libreharness-mirror.service` with your checkout paths, and
  `--lock-file %t/libreharness-mirror.lock --status-file %S/libreharness/mirror-status.json`
- `libreharness-mirror.timer`
- `libreharness-mirror-check.service` with the same `--status-file`
- `libreharness-mirror-check.timer`
- `libreharness-mirror-alert.service`

Then enable both timers and allow the user manager to run while logged out:

```sh
systemctl --user daemon-reload
systemctl --user enable --now libreharness-mirror.timer libreharness-mirror-check.timer
loginctl enable-linger "$USER"
```

The script refuses to rewrite a GitHub `main` that has commits not in Gitea. It
leaves GitHub-only tags and branches alone. A tag conflict fails the run instead
of rewriting history.

## Releases

Tags are mirrored. GitHub releases are a separate GitHub-side artifact; the
mirror does not create, publish, or delete them.
