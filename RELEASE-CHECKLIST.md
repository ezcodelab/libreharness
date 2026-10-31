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
- [x] Python queue tests: 16 passed; the Harbor adapter configure test passed
  under a Harbor venv and is skipped when Harbor is not installed.
- [x] Node tests: auto-intake, goal-watch, review-protocol, security-guard,
  installer.
- [x] Docs lint: 62 Markdown files, no problems.
- [x] SPDX headers: all checked files pass.
- [x] Private-path scan: no findings.
- [x] Benchmark runner `--dry-run`, score no-data path, and analyzer no-data
  path.
- [x] External benchmark selected: Terminal-Bench 2.0 via Harbor. Plain
  OpenCode is the before baseline; the local B1-B8 suite is only a supplement.
- [x] Harbor adapter imports as `harbor_agent.opencode_agent:OpenCodeLibreHarness`,
  passes `harbor agent auth`, and uploads the expected paths in a fake sandbox.
- [x] No `free-explore` or `flash-fallback` code remains.

## Not proven

- [ ] Live OpenCode session from the clean `HOME`. The temporary home has no
  provider credentials, so this was not run.
- [ ] GitHub Actions workflows were not executed on GitHub. They were inspected
  and the same local commands pass.
- [ ] Terminal-Bench 2.0 via Harbor is not a full run. A two-task pilot passed
  on both arms with no quality delta; one task was cancelled by the outer
  timeout. The local B1-B8 suite has no fixtures or run data.
- [x] The `harbor_agent` adapter completed live Harbor trials on
  gpt2-codegolf and break-filter-js-from-html with clean harness exits.
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
