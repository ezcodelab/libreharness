<!-- SPDX-License-Identifier: MIT -->

# Governance

## Maintainer

One maintainer owns 1.0.0: the person or project role listed in the repository
profile. The maintainer makes the final call on scope, releases, and one-way
decisions. The role is expected to grow into a small maintainer group after
the first public release; this candidate does not pretend that group exists
yet.

The maintainer is responsible for:

- keeping the public tree free of secrets, private paths, and personal data;
- reviewing changes for correctness, safety, scope, and evidence;
- deciding when a release is ready;
- recording one-way decisions and their alternatives;
- saying "not run" or "unproven" when that is the truth.

## One-way gates

A one-way decision is hard or expensive to reverse. The maintainer must stop,
explain why it is one-way, list at least two alternatives with tradeoffs, and
ask for explicit approval in the current discussion before committing.

| Area | Examples | Why it is a gate |
|---|---|---|
| License | Changing MIT or CC BY 4.0, adding a dependency with a different license | Hard to reverse after contributions and releases |
| Publication and history | Making a repository public, publishing history, changing the project name | Public data cannot be recalled |
| State schema | Changing the task file layout, status names, or migration behavior | Breaks existing queues and tooling |
| Auth and permissions | Changing the trust boundary, adding a credential store, widening shell access | Security impact |
| Public interface | Command names, CLI flags, environment variables, Jev adapter contract | Users and adapters depend on it |
| Infrastructure and CI | Changing release automation, secrets handling, or hosted services | Can expose data or break releases |
| Tenancy and accounts | Adding a hosted account system or multi-tenant service | Changes the product boundary |
| Major dependency | Replacing the stdlib queue or adding a runtime package | Maintenance, supply chain, and portability |

A two-way decision, such as a wording fix, a test, or an internal refactor
with no interface change, is decided and acted on without a gate.

## Issues

- Use the issue templates when they are available.
- One issue should describe one problem or one proposal.
- Do not include a secret, private path, customer data, or a full transcript.
- A bug report should include the version, platform, reproduction, expected
  behavior, actual behavior, and the smallest relevant output.
- A feature request should state the problem, the proposal, the alternatives,
  and whether it changes a public interface.
- A security report follows [SECURITY.md](SECURITY.md), not the public issue
  tracker.

## Pull requests

- One task, one reviewable diff. Link the task or issue.
- Include the exact checks run and their results. "Tests pass" without a
  command and output is not evidence.
- New behavior needs a test or a measured check.
- New files need an SPDX header and, for documentation, a working relative
  link.
- The author signs off with `git commit -s`.
- A maintainer reviews proportionally to risk. Auth, secrets, data, public
  interfaces, recovery, and concurrency get an independent review.
- A confirmed high-severity finding blocks. A lower-severity finding is fixed
  or explicitly accepted with a reason.
- Do not force-push a shared branch, rewrite shared history, or push directly
  to `main`.

## Releases

- Versions follow semantic versioning. `1.0.0-rc.1` is a release candidate, not
  a stable release.
- Every release has a changelog entry, a tag, and a note that states what was
  verified and what was not.
- Patch and minor releases keep the Markdown state format backward compatible.
  A major release that changes the state layout ships a migration script and a
  backup step.
- Release checks run on the tagged tree. A green branch is not a green release.
- A performance claim needs the pre-registered protocol, fixed task set, raw
  data, analysis script, manifest, and limitations. Without them, the release
  says "benchmark unrun".
- A release artifact is scanned after it is built, not only before.
- Rollback means checking out the previous tag and restarting. State under
  `HARNESS_STATE` is preserved.

## Changes to this document

Open a pull request with the proposed change and the reason. The maintainer
approves. A change that weakens the one-way gate or the evidence rule needs an
explicit decision entry, not a silent edit.
