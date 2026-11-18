<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Autonomy and completion

This is the operating contract for agents in this workspace. It is deliberately
short enough to follow under pressure. The forge mechanics are in
[auto-merge.md](auto-merge.md); the Gitea mirror is in [mirror.md](mirror.md).

## Own the exit condition

Before the first edit, turn the request into a checkable predicate: the task
acceptance, the commands that prove it, and the artifact a reviewer can rerun.
Then drive to that predicate. A plateau is not a stop. Never relax the predicate
to declare victory.

This is the `autonomous-run` pattern from Lauren Tan's pstack (poteto-mode): the
agent owns the exit condition and iterates until the predicate is met. See
[pstack autonomous-run](https://github.com/backnotprop/pstack/blob/main/skills/poteto-mode/playbooks/autonomous-run.md).

## Act, do not ask for reversible work

Do the work you can undo. Ask only for a one-way door or a real fork in the
product:

- irreversible writes: deploy, data deletion, force-push to shared history,
  account or permission changes;
- a genuine product, policy, or preference call that no check can settle;
- a true dead end with a concrete next action.

"Do not stop for permission" is not "never ask". It means the default is action,
and the exception is named. This mirrors pstack's autonomy rule and OpenCode's
two-way-door rule.

## Auto-merge is the default

Open every PR ready, never as a draft. Once the required checks are green and an
independent reviewer has returned `PASS` or `PASS+NOTES` for the exact head,
merge it. Do not leave a reviewed, green PR for the operator.

Green CI alone is not a review. The reviewer must not have written the patch,
and it must exercise the real artifact, not just read the diff. This follows the
pstack `shipping` rule: verify independently, then land only the verified run.
See [pstack shipping](https://github.com/backnotprop/pstack/blob/main/skills/poteto-mode/playbooks/shipping.md).

The forge gate proves CI, not the reviewer's identity. Independence is an
agent-protocol requirement: a fresh context that did not write the patch. A
forge approval would require a second account and would block unattended merge;
when a repository has one, require it as well. A local `PASS` file is a process
record, not forge-verified proof.

The exception is the gate itself. A change that edits or loosens a gate, CI,
auth, or deploy path needs an independent review and an operator merge, because
the gate cannot certify its own weakening. That merge belongs to the same task;
it is not a deferred PR.

## No deferral

In-scope discoveries are finished in the same task. Out-of-scope work becomes a
task with an owner and acceptance, not a "later" note. A task is not `done`
with:

- an unchecked acceptance item;
- an unmerged PR, a failing check, or a red gate;
- a deferred or "follow-up" list that is part of the original scope;
- a worktree, branch, process, or temp file you created.

A task may be `blocked` only for an operator-only decision or a true dead end.
The blocker names the exact question or next action, and the task is picked up
again when that answer exists. `blocked` is not a synonym for "I ran out of
time."

## Finish the cleanup

After the merge:

- confirm the PR reads merged, not queued;
- delete the branch and worktree you created;
- stop processes and remove temp files you started;
- leave the checkout clean on `main` tracking the canonical remote;
- close superseded PRs with evidence, not silence.

## Forge matrix

| Repository kind | Canonical forge | Contribution path | Merge path |
|---|---|---|---|
| Public: Credarr, LibreHarness | GitHub | ready GitHub PR | GitHub Actions gate with `GITHUB_TOKEN` |
| Gitea-canonical: Brain and the homelab repos | Gitea | AGit PR to `refs/for/main/<topic>` | repository gate on `pull_request_target` with the repo `MERGE_TOKEN` secret |
| Gitea mirror of a public repo | Gitea (read-only) | none | Gitea pulls GitHub; never push or open a PR there |

Agents hold no personal token. The Gitea gate secret is repository-scoped and
available only to the gate job, which never checks out PR code. If a repo is
missing a gate or a required check, that is a defect in the repo, not a reason
to hand an agent a token.

## Enforcement

The contract is not only prose:

- `AGENTS.md` carries the rule into every session.
- Each Gitea repo has a base-controlled gate, a `.github/merge-policy.json`, a
  repository `MERGE_TOKEN` secret, and branch protection that requires CI plus
  the gate check.
- The task tool refuses `done` without concrete, fully checked acceptance, and
  with a non-empty `Deferred` or `Follow-ups` section.
- Branch, worktree, process, and temp-file cleanup is a reviewed protocol step;
  the task tool cannot see the forge or the process table.
- The gate refuses protected paths, forbidden files, drafts, blocking labels,
  moved heads, and missing policy.
- CI turns repeated failures into tests or lints, following pstack's
  `principle-encode-lessons-in-structure`.

Adding an active Gitea repo is not complete until all four exist. Put the gate
in the scanned workflow directory (`.gitea/workflows/` if it exists, otherwise
`.github/workflows/`), add the policy, create the secret, and require both
checks. Then verify the copies have not drifted:

```sh
python3 bin/sync_gitea_gate.py --check \
  --target ../brain --target ../aequitas \
  --target ../homelab-applications --target ../homelab-infrastructure
```

A repo missing the gate is not eligible for agent work; fix the repo, do not
give the agent a token.

## References

- [pstack poteto-mode](https://github.com/backnotprop/pstack)
- [autonomous-run](https://github.com/backnotprop/pstack/blob/main/skills/poteto-mode/playbooks/autonomous-run.md)
- [shipping](https://github.com/backnotprop/pstack/blob/main/skills/poteto-mode/playbooks/shipping.md)
- [worker rules](https://github.com/backnotprop/pstack/blob/main/skills/poteto-mode/worker.md)
- [Gitea gate template](../templates/gitea-auto-merge.yml)
