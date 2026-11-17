<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Trusted Gitea auto-merge

Gitea is canonical. Agents open pull requests over SSH with AGit; no agent
needs a long-lived Gitea token. A scoped workflow on the protected base of the
consuming repository decides whether an eligible PR merges.

## Open a PR without a token

```sh
git push origin HEAD:refs/for/main
```

Gitea creates the pull request from the pushed head. Use a topic suffix, such as
`refs/for/main/fix-login`, when the branch name is not descriptive.

## Trust model

The gate is a **scoped workflow** from `admin/libreharness` at
`.gitea/scoped_workflows/auto-merge.yml`, pinned to that repository's default
branch. It is registered once at the owner level and marked required. It runs
in each consuming repository with that repository's runner, secrets, and
short-lived `GITEA_TOKEN`. Consumer PRs cannot edit the workflow that judges
them.

The consumer base branch provides the trusted scripts:

- `bin/pr_policy.py`
- `bin/pr_status.py`
- `bin/pr_merge.py`
- `bin/verify_pr.sh` for repo-specific checks; LibreHarness runs docs, SPDX,
  and the private-path scan there

The workflow checks out the consumer base and the PR tree. It executes only the
base scripts; it never executes PR code. Fork PRs are excluded.

The scoped workflow pins SHA-256 hashes for the generic consumer scripts
(`pr_policy.py`, `pr_status.py`, `pr_merge.py`, `scan_private.py`) and refuses
to run if a consumer copy drifts. `verify_pr.sh` is the repo-specific hook.

| Job | Repository access | PR code | What it does |
|---|---|---|---|
| `verify` | read | checks out the tree, never executes it | Runs the trusted base policy and scanners against the PR tree. |
| `publish` | write | none | Sets the `verifier / policy` commit status from the verify result. |
| `merge` | write | none | Re-reads the PR, requires a successful `verifier / policy` status, then schedules the merge. |

The write jobs do not check out or execute the PR. The only token is Gitea's
short-lived, repository-scoped Actions token (`GITEA_TOKEN`); no personal token
is distributed to agents.

## One-time source registration

An owner or site administrator registers `admin/libreharness` at
**User Settings -> Actions -> Scoped Workflows**. The workflow is limited to
`admin/libreharness` and `admin/credarr`; other owner repos skip it.

Do not mark it required globally while other owner repos are unprotected: add
the exact scoped status context
`admin/libreharness: auto-merge / verify (pull_request_target)` to the branch
protection of the two target repositories. The workflow also publishes
`verifier / policy`; `pr_merge.py` requires it. Gitea enforces branch-protection
contexts only on protected branches.

## What the verifier checks

`bin/pr_policy.py` checks the PR metadata and diff:

- open, not merged, not a draft, base `main`, head SHA matches the event
- same-repository head, not a fork
- no `do-not-merge`, `no-auto-merge`, or `wip` label
- at most 50 changed files and 2000 changed lines
- no protected paths: workflows, scoped workflows, policy/auth/mirror scripts,
  `AGENTS.md`, `SECURITY.md`, build and dependency manifests, `ops/`
- no forbidden files such as private keys, `.env`, or secret files
- no private markers or private keys in added diff lines

The `verify` job also runs the trusted private-path scan, SPDX check, docs lint,
gitleaks with the base config, and `git diff --check` against the PR tree. It
rejects added symlinks and submodules.

## Merge behaviour

The `merge` job calls the Gitea merge API with:

```json
{
  "do": "merge",
  "merge_when_checks_succeed": true,
  "head_commit_id": "<verified head>",
  "delete_branch_after_merge": false
}
```

A merge commit preserves the PR head as an ancestor, so the public mirror can
fast-forward without rewriting GitHub. The head is pinned; a moved head is
refused. Branch protection must require the scoped verifier status and the
repository CI checks.

## Protected paths

Changes to the gate itself, build/dependency manifests, and other protected
paths intentionally cannot auto-merge. A gate change requires an
operator-supplied `GITEA_TOKEN` and the verified `pr_watch` path; see the
command reference. Do not add a local token shim or distribute the token to
agents. The default agent path is AGit plus the trusted scoped workflow.

## Failure behaviour

If any verify step fails, `publish` sets `verifier / policy` to failure and
`merge` does not run. Fix the branch and push again; the synchronize event
creates a fresh run for the new head. A PR that is closed, draft, retargeted, or
labelled for blocking is never auto-merged.
