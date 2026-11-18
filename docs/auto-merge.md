<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Trusted GitHub auto-merge

GitHub is canonical for **Credarr** and **LibreHarness**. Gitea is a read-only
mirror. Agents open GitHub pull requests; the merge gate runs on GitHub Actions
with the short-lived `GITHUB_TOKEN`.

## Open a PR

Open a normal GitHub pull request from a branch or a fork. No agent token is
needed. Draft PRs are ignored; mark the PR ready when it is reviewable.

## Trust model

`.github/workflows/auto-merge.yml` on the default branch uses
`pull_request_target`, so the workflow that judges a PR comes from the protected
base branch, not from the PR head.

| Job | Token | PR code | What it does |
|---|---|---|---|
| `verify` | read-only | checks out the PR merge ref, never executes it | Runs the trusted base policy and scanners against the PR tree. |
| `merge` | write | none | Waits for required checks, then merges the exact verified head. |

The merge job never checks out or runs PR code. The only token is GitHub's
short-lived, repository-scoped Actions token. No personal token is distributed
to agents.

Fork PRs are supported: the verify job is read-only and scans the merge ref in
the base repository; the merge job has no checkout.

## What the verifier checks

`bin/pr_policy.py --forge github` checks the GitHub PR metadata and diff:

- open, not merged, not a draft, base `main`, head SHA matches the event
- a non-empty head repository; fork heads are allowed
- no `do-not-merge`, `no-auto-merge`, or `wip` label
- at most 50 changed files and 2000 changed lines
- no protected paths: workflows, policy/mirror scripts, `AGENTS.md`,
  `SECURITY.md`, build and dependency manifests, deploy scripts
- no forbidden files such as private keys, `.env`, or secret files
- no private markers or private keys in added diff lines

The `verify` job also runs the trusted private-path scan, SPDX check, docs lint,
gitleaks with the base config, and `git diff --check` against the PR tree. It
rejects added symlinks and submodules.

## Branch protection

Require `auto-merge / verify` and the repository CI checks on `main`. Disable
force pushes and branch deletion. The merge job waits for those required checks
with `gh pr checks --watch --required` and merges with
`gh pr merge --merge --match-head-commit`.

## Gitea mirror

Gitea pulls GitHub `main` and tags and is read-only. It does not accept PRs and
never pushes to GitHub. See [the mirror doc](mirror.md).

## Protected paths and gate changes

Changes to the gate workflow, policy scripts, build/dependency manifests, and
deploy scripts cannot auto-merge. A gate change requires a manual reviewed
merge. Do not add a local token shim or distribute a token to agents.

## Failure behaviour

If verification fails, the `auto-merge / verify` check fails and the merge job
does not run. Fix the branch and push again. A PR that is closed, draft,
retargeted, or labelled for blocking is never auto-merged.
