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
`libreharness-mirror.timer`.

The script refuses to rewrite a GitHub `main` that has commits not in Gitea. It
leaves GitHub-only tags and branches alone. A tag conflict fails the run instead
of rewriting history.

## Releases

Tags are mirrored. GitHub releases are a separate GitHub-side artifact; the
mirror does not create, publish, or delete them.
