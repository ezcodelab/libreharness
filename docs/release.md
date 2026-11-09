<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Release checklist

Status: **procedure for 1.1.0.** Linux only, OpenCode only. The public
repository is `https://github.com/ezcodelab/libreharness`, and npm trusted
publishing is configured for `ezcodelab/libreharness` and `release.yml`.

This page is the release gate. A green branch is not a green release. Run the
checks on the tagged tree, and do not publish from a dirty working tree.

## 1. Confirm the release scope

- [ ] The version is `1.1.0` in `package.json`, `bin/libreharness.js`, and
  `CHANGELOG.md`.
- [ ] `README.md`, `docs/README.md`, and `SECURITY.md` say Linux only and
  OpenCode only.
- [ ] The plugin entry in `docs/install.md` is the normal
  `"plugins": ["libreharness@1.1.0"]` form, with the four agent stubs.
- [ ] State defaults to `~/.local/state/libreharness`, is created with mode
  700, and is a real directory rather than a symlink.
- [ ] No macOS, Windows, Claude Code, Hermes, or other host-support claim is
  present.
- [ ] No benchmark result is claimed. The benchmark remains unrun.
- [ ] The working tree is clean and the release commit is reviewed.

## 2. Run the checks

```sh
python3 -m compileall -q bin tests
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/auto-intake.test.mjs
node tests/goal-watch.test.mjs
node tests/review-protocol.test.mjs
node tests/security-guard.test.mjs
node tests/plugin.test.mjs
node tests/installer.test.mjs
python3 bin/docs_lint.py . --skills-dir skills
python3 bin/check_spdx.py --root .
python3 bin/scan_private.py --root .
git diff --check
# CI installs a pinned gitleaks binary and scans with the repository config.
gitleaks detect --source . --config .gitleaks.toml --redact --verbose
```

Record the command and result in the release task or tag note. Do not treat a
skipped test as a pass.

## 3. Inspect the package

```sh
npm pack --dry-run
npm pack
```

Inspect the tarball contents. It must include the runtime, commands, skills,
agents, plugins, docs, and `harbor_agent/`. It must not include state, jobs,
results, caches, credentials, or private files.

Install the packed artifact into a temporary Linux prefix and start an isolated
OpenCode service with only the plugin entry and the four agent stubs:

```sh
tmp=$(mktemp -d)
npm install --prefix "$tmp" ./libreharness-1.1.0.tgz
# Write a minimal opencode.json with:
#   "plugins": ["$tmp/node_modules/libreharness"]
#   four empty agent stubs
# Then confirm the plugin is active, commands/skills load, the four agent
# prompts are filled, and ~/.local/state/libreharness is created mode 700.
```

Do not install the package into the release checkout.

## 4. Prepare the public remote

The public GitHub remote is `git@github.com:ezcodelab/libreharness.git`. The
self-hosted `origin` remote is a development mirror; do not treat it as the
public target.

- [ ] Confirm the GitHub repository is the intended public target.
- [ ] Confirm the public tree contains no archived experiment reports, old
  suites, jobs, results, caches, secrets, or private paths.
- [ ] Confirm the README and LICENSE render correctly on the host.
- [ ] Confirm the host's private vulnerability reporting and conduct reporting
  paths exist.
- [ ] Do not push directly to `main`. Push a release branch, open a pull
  request, let CI pass, and merge through the host.

If the public history must be clean, create the repository from a fresh
snapshot. The current repository history contains old experiment files by
explicit operator decision; do not assume a clean tree means a clean history.

## 5. First publish bootstrap (done for 1.0.0)

The first publish needs one interactive 2FA approval because trusted
publishing can only be configured on a package that already exists. That step
is complete for `libreharness`. A new package name would repeat it:

```sh
npm login
npm stage publish --access public
npm stage list <package>
```

Approve the staged version on npmjs.com with your passkey, then verify:

```sh
npm view libreharness@<version> version
```

## 6. Trusted publishing (configured)

The package trusts GitHub Actions from `ezcodelab/libreharness` and
`release.yml`. The release workflow uses OIDC; there is no `NPM_TOKEN` secret
and no long-lived publish token. The workflow upgrades npm explicitly because
Node 22's bundled npm 10 cannot use trusted publishing. Reconfigure only if the
repository, workflow filename, or package owner changes:

```sh
npm trust github --file release.yml \
  --repo ezcodelab/libreharness --allow-publish
```

Keep the package's **Publishing access** at "Require two-factor authentication
and disallow tokens".

## 7. Tag and publish

Only after the checks, the package inspection, and the public repository
review:

```sh
git tag -s v1.1.0 -m "LibreHarness 1.1.0"
git verify-tag v1.1.0
git push github v1.1.0
```

The maintainer verifies the tag locally before pushing. The release workflow
checks the version and package, reruns the checks, publishes over OIDC, builds
an archive, and creates the host release. The tag push is the publication
approval. The publish step skips a version that already exists, so a manual
publish and a later tag release cannot collide.

Do not push a tag before the version and changelog are final. Do not force-push
a shared branch.

## 8. Post-release verification

- [ ] Install from the published npm package on a clean Linux host.
- [ ] Confirm the plugin is active, the commands and skills load, the four
  agents have prompts, and state is created at `~/.local/state/libreharness`
  with mode 700.
- [ ] Run `npx libreharness init --dry-run` and a real init in a temporary
  OpenCode config.
- [ ] Confirm `/goal`, `/review`, `/close`, `/tune`, and `/state-audit` are
  discoverable.
- [ ] Confirm `doctor.py` passes and state stays outside the checkout.
- [ ] Confirm the release notes link to the changelog and state the benchmark
  is unrun.
- [ ] Confirm the package tarball and release archive hashes match.

## 9. Rollback

- Unpublish only if the host and registry allow it; otherwise publish a patch
  release with a clear advisory.
- Point users at the previous tag and restore `HARNESS_STATE` from backup if a
  migration was involved.
- Never rewrite a published tag or force-push the public `main`.

## Release gates that still need a human

- Signed tag and signing key.
- npm publication approval (the tag push triggers it).
- Public release announcement.
- Any change to the Linux-only or OpenCode-only scope.
