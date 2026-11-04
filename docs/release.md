<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Release checklist

Status: **procedure for 1.0.0. Not yet executed.** Linux only, OpenCode only.

This page is the release gate. A green branch is not a green release. Run the
checks on the tagged tree, and do not publish from a dirty working tree.

## 1. Confirm the release scope

- [ ] The version is `1.0.0` in `package.json`, `bin/libreharness.js`, and
  `CHANGELOG.md`.
- [ ] `README.md`, `docs/README.md`, and `SECURITY.md` say Linux only and
  OpenCode only.
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

Install the packed artifact into a temporary Linux prefix and run the doctor:

```sh
tmp=$(mktemp -d)
npm install --prefix "$tmp" ./libreharness-1.0.0.tgz
python3 "$tmp/node_modules/libreharness/bin/doctor.py" \
  --root "$tmp/node_modules/libreharness"
```

Do not install the package into the release checkout.

## 4. Prepare the public remote

The current GitHub remote is `https://github.com/ezcodelab/libreharness.git`
(private until publication). The SSH form is
`git@github.com:ezcodelab/libreharness.git`.

- [ ] Confirm the GitHub repository is the intended public target.
- [ ] Add it as a separate remote; do not reuse a private remote blindly.
- [ ] Confirm the public tree contains no archived experiment reports, old
  suites, jobs, results, caches, secrets, or private paths.
- [ ] Confirm the README and LICENSE render correctly on the host.
- [ ] Confirm the host's private vulnerability reporting and conduct reporting
  paths exist.
- [ ] Add a real `.github/CODEOWNERS` owner if the host requires one. The
  placeholder was removed before publication.

If the public history must be clean, create the repository from a fresh
snapshot. The current repository history contains old experiment files by
explicit operator decision; do not assume a clean tree means a clean history.

## 5. Tag and publish

Only after the checks and the public repository review:

```sh
git tag -s v1.0.0 -m "LibreHarness 1.0.0"
git verify-tag v1.0.0
git push <public-remote> main
git push <public-remote> v1.0.0
```

The maintainer verifies the tag locally before pushing. The release workflow
checks the version and package, reruns the checks, publishes the npm package
when the `NPM_TOKEN` repository secret is configured, builds an archive, and
creates the host release. The tag push is the publication approval. The publish
step skips a version that already exists, so a manual first publish and a later
tag release cannot collide:

```sh
npm publish --access public
```

Do not push a tag before the version and changelog are final. Do not force-push
a shared branch.

## 6. Post-release verification

- [ ] Install from the published npm package on a clean Linux host.
- [ ] Run `npx libreharness init --dry-run` and a real init in a temporary
  OpenCode config.
- [ ] Confirm `/goal`, `/review`, `/close`, and `/tune` are discoverable.
- [ ] Confirm `doctor.py` passes and state stays outside the checkout.
- [ ] Confirm the release notes link to the changelog and state the benchmark
  is unrun.
- [ ] Confirm the package tarball and release archive hashes match.

## 7. Rollback

- Unpublish only if the host and registry allow it; otherwise publish a patch
  release with a clear advisory.
- Point users at the previous tag and restore `HARNESS_STATE` from backup if a
  migration was involved.
- Never rewrite a published tag or force-push the public `main`.

## Release gates that still need a human

- Public host and remote URL.
- Signed tag and signing key.
- npm publication and token.
- Public release announcement.
- Any change to the Linux-only or OpenCode-only scope.
