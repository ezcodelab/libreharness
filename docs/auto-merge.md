<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Trusted auto-merge

GitHub is canonical for **Credarr** and **LibreHarness**. Gitea is a read-only
mirror. Agents open GitHub pull requests; the merge gate runs on GitHub Actions
with the short-lived `GITHUB_TOKEN`. The operating contract, including the
no-deferral rule and the auto-merge default, is in
[autonomy.md](autonomy.md).

## Open a PR

Open a normal GitHub pull request from a branch or a fork. No agent token is
needed. Draft PRs are ignored; mark the PR ready when it is reviewable.

`origin` is GitHub in the local checkouts; `gitea` is the read-only mirror. Run
`git config core.hooksPath .githooks` once per clone; the pre-push hook rejects
the mirror.

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

## GitHub Actions policy

GitHub's default policy blocks `pull_request_target` in public repositories from
2026-12-02 unless an applicable Actions policy explicitly allows it. Both
Credarr and LibreHarness have an active repository policy that allows only
`.github/workflows/auto-merge.yml` to use `pull_request_target`. If the policy
is removed or the workflow path changes, the gate will not run.

## Gitea mirror

Gitea pulls GitHub `main` and tags and is read-only. It does not accept PRs and
never pushes to GitHub. See [the mirror doc](mirror.md).

## Gitea-canonical repositories

Every active Gitea-canonical repository, public or private, uses the same
base-controlled gate at
`.github/workflows/auto-merge.yml` on `pull_request_target`, plus a
`.github/merge-policy.json` that lists the repository's protected paths. The gate
job has no checkout; it validates the PR and schedules
`merge_when_checks_succeed` with a repository `MERGE_TOKEN` secret. Branch
protection requires the repository CI check and
`auto-merge / gate (pull_request_target)`. The policy, workflow, auth, and
deploy paths require a manual operator merge. Agents push AGit PRs and hold no
token. Use a dedicated bot token for `MERGE_TOKEN`; the gate job never checks out
PR code.

Gitea scans `.gitea/workflows/` first. If that directory exists, it ignores
`.github/workflows/` completely. The gate must live in the scanned directory,
and moving a repository between layouts is a manual gate change. `bin/
sync_gitea_gate.py` writes to the correct directory and fails if a stale copy
exists in the other one.

The gate accepts same-repository branches only. A fork PR needs a manual review
and merge because the gate cannot prove the fork's CI workflow. The gate refuses
a missing or malformed policy, a draft, a blocking label, a moved head, a
protected path, or a forbidden file. After the file scan it re-reads the PR and
re-checks state, head, labels, and mergeability, so the tree it inspected is the
head it pins. Branch protection must also require the repository CI check; the
gate schedules the merge but does not substitute for CI.

## Autonomy

Open every PR ready. Auto-merge is the default after independent review and
green required checks; do not leave a green, reviewed PR for the operator. The
review must be from an agent or person that did not write the patch, and it must
exercise the real artifact, not only read the diff. A `PASS` or `PASS+NOTES`
verdict is tied to the exact head.

The exception is a change that edits or loosens a gate, CI, auth, or deploy
path. It gets independent review and an operator merge in the same task. The
gate cannot certify its own weakening.

## Protected paths and gate changes

Changes to the gate workflow, the merge policy, policy scripts, build and
dependency manifests, and deploy scripts cannot auto-merge. A gate change
requires a manual reviewed merge. Repo admins can use the GitHub admin override
for these changes after review; the auto-merge bot cannot. Do not add a local
token shim or distribute a token to agents.

## Failure behaviour

If verification fails, the `auto-merge / verify` check fails and the merge job
does not run. Fix the branch and push again. A PR that is closed, draft,
retargeted, or labelled for blocking is never auto-merged.

## First proof

The GitHub gate was first exercised on 2026-11-17 with a docs-only PR.
