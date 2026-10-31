<!-- SPDX-License-Identifier: MIT -->

# Release checklist

Status: **local release candidate, 2026-10-30. Not published.**

Tree: **LibreHarness** 1.0.0-rc.1, local clone checkout on branch `main`.
`origin` points at the local Gitea repository. This is a local Gitea test
publication, not a public release; no tag or public announcement exists.

Name check: GitHub has no `LibreHarness` user, organization, or repository, and
`libreharness` is free on npm and PyPI. `FreeHarness` is taken by an
organization, two similar repositories, and an npm package.

## Passed

- [x] Fresh one-commit history on `main`, pushed to the local Gitea
  `origin/main`.
- [x] One-command npm-tarball install in a clean temporary `HOME`; doctor
  passed.
- [x] Clean temporary `HOME` copy of the tree.
- [x] `bin/doctor.py`: checkout, state outside checkout, Python, Node, Git,
  config parse, plugin syntax, queue help.
- [x] Queue round trip in a temporary state root: create, claim, review, done
  with evidence, generated board.
- [x] Jev mock review without a key or network call.
- [x] Full Python suite: 30 tests passed, including 5 Harbor adapter tests and
  9 ablation tests. The adapter tests are skipped when Harbor is not installed.
- [x] Node tests: auto-intake, goal-watch, review-protocol, security-guard,
  installer.
- [x] Docs lint: 66 Markdown files, no problems.
- [x] SPDX headers: all checked files pass.
- [x] Private-path scan: no findings.
- [x] Benchmark runner `--dry-run`, score no-data path, and analyzer no-data
  path.
- [x] External benchmark selected: Terminal-Bench 2.0 via Harbor. Plain
  OpenCode is the before baseline; the local B1-B8 suite is only a supplement.
- [x] Harbor adapter imports as `harbor_agent.opencode_agent:OpenCodeLibreHarness`,
  passes `harbor agent auth`, and uploads the expected paths in a fake sandbox.
- [x] Harbor adapter overlay upload is wired through `setup()`, the hook Harbor
  0.25.0 calls. An install-only job (`2026-10-31__14-11-55`) shows the overlay
  `mkdir` after OpenCode 1.19.5 installs.
- [x] No `free-explore` or `flash-fallback` code remains.

## Not proven

- [ ] Live OpenCode session from the clean `HOME`. The temporary home has no
  provider credentials, so this was not run.
- [ ] GitHub Actions workflows were not executed on GitHub. They were inspected
  and the same local commands pass.
- [ ] Terminal-Bench 2.0 via Harbor is not a full run. The two-task pilot was
  adapter-only: its `configure()` overlay upload was dead code, so it did not
  run LibreHarness. It is not a harness result. One task was cancelled by the
  outer timeout. The local B1-B8 suite has no fixtures or run data.
- [ ] A live Harbor task after the `setup()` overlay fix has not run. The
  install-only job proves the upload calls, but the model run and auth mapping
  remain unproven. Run the one-task smoke in a shell with `OLLAMA_API_KEY`.
- [ ] Live Jev endpoint call. Only the mock path was exercised.
- [ ] `JEV_MODE` is documented as an adapter contract but is not read by the
  rc.1 clients.
- [ ] `bin/jev_common.py` and `jev/prompts/` are still future refactors.
- [ ] Windows support. 1.0.0 is Linux/macOS; 1.1 is a preview.
- [ ] Public name, owner, license, and history approval.

## One-way gates still missing

| Gate | Decision | Status |
|---|---|---|
| G0 | Public repository name and owner | **LibreHarness** chosen; local Gitea owner pending |
| G0 | Fresh sanitized history | **Approved**; local git history initialized |
| G1 | MIT code and CC BY 4.0 docs | **Approved** |
| G2 | Benchmark claims | No claims, no data |
| G3 | Release candidate sign-off | Local checks pass; independent review accepted |
| G4 | Public repository and history publication | Not performed |

Publication still requires explicit human approval in the current turn. Nothing
in this checklist authorizes a push, a public repository, or a release.

## Next actions before publication

1. Choose the public name and owner, then approve G0.
2. Approve the MIT and CC BY 4.0 split, then approve G1.
3. Pin GitHub Actions to commit SHAs and run the workflows on a fork-like
   clone.
4. Run at least one live OpenCode quickstart with a disposable provider key.
5. Run plain OpenCode and LibreHarness on Terminal-Bench 2.0 via Harbor before
   making any benchmark claim. Build the local B1-B8 fixtures only for fast
   regression.
6. Publish only after G4 approval.
