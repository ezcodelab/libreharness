<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Design notes

These notes explain why the harness looks like this and which alternatives were
rejected. They are not a roadmap promise.

## Why a Markdown queue

A task is one Markdown file with frontmatter and a few fixed sections. The
board is generated from the files.

Why:

- **Inspectable.** A person can read a task without a tool.
- **Diffable.** A task change is a text diff. It can be reviewed like code.
- **Portable.** No database, server, driver, or migration service.
- **Crash-safe enough.** Writes use a temporary file, `fsync`, and atomic
  replace. A crash does not leave a half-written task.
- **Cheap to delete.** Removing a state directory removes the queue. There is
  no orphaned database.
- **Testable.** The queue is stdlib Python and a temporary directory.

Tradeoffs:

- No query engine. Listing is a directory scan.
- No built-in encryption. Filesystem permissions and disk encryption are the
  boundary.
- No schema migration framework. A major format change needs a script.
- Markdown parsing is deliberately simple. A task is not a rich document.
- POSIX `fcntl` locking means Windows is out for 1.0.0.
- A large queue eventually needs archive and retention rules.

The queue is not trying to be a project tracker. It is a small durable memory
for one operator or a small team.

## Why one task, one reviewable diff

A task should fit one agent session and one reviewable diff. That constraint
does three things:

1. It keeps context small enough to load.
2. It makes the review boundary obvious.
3. It prevents a "task" from becoming an unfinishable project.

When a request is larger, `/goal` splits it into children by deliverable and
review boundary. A one-way decision becomes a decision-memo child, not an
implementation child.

## Why the evidence gate

The queue refuses to mark a task done with `none`, `ok`, `pass`, `done`, or
`tests pass`. It needs a command and result, a measured check, or `[T]` with a
plan.

Why:

- "Tests pass" without output is a claim, not evidence.
- A model can be confident and wrong. A command result is harder to fake.
- A future reader needs to know what was actually checked.
- A tracked deferral is better than a false pass.

The gate is enforced in the queue, not in a prompt. A prompt can be ignored; a
status transition cannot.

Tradeoffs:

- It adds friction to a small change. That is why trivial work can skip the
  queue.
- It can encourage a performative command. The answer is review, not a weaker
  gate.
- It does not prove the check was the right one. Acceptance quality is still a
  human judgment.

## Why Jev asks typed questions

A chat review returns prose. Prose is hard to compare across diffs, models, and
dates. A typed question returns a score, a probability, or a choice. That makes
the answer:

- comparable across runs;
- calibratable against human labels;
- testable with a mock;
- separable by axis, so a send-back names what failed;
- replaceable at the transport layer.

The seven axes are a checklist, not a theory of quality. They exist to make the
review specific: performance, size, maintainability, simplicity, reliability,
scalability, and security.

## Why Jev is advisory

A typed answer is still an answer from a model. It can be wrong, stale, or
manipulated by text in the diff. Making it a hard gate would:

- give a model the power to block a correct change;
- encourage prompt gaming;
- hide the human decision;
- make a benchmark compare the gate, not the work.

Jev is evidence. The operator or reviewing agent decides. A send-back needs a
fix or an explained disagreement. A pass does not replace the acceptance check.

## Rejected alternatives

| Alternative | Why it was rejected |
|---|---|
| A database-backed queue | Adds a service, driver, migration, backup, and failure mode for a small workflow. A Markdown file is enough. |
| One JSON or YAML file for all tasks | Merge conflicts, partial writes, and a whole-file rewrite for one status change. One file per task is simpler. |
| A hosted task service | Changes the privacy boundary and the product from a local harness to a service. Out of scope. |
| A single TODO list | No ownership, dependencies, evidence, handoff, or review boundary. It loses the reason for the queue. |
| Automatic Jev gate | False confidence and model-controlled blocking. Advisory is the safer default. |
| A general multi-agent framework in 1.0.0 | Coordination cost, unclear ownership, and no tests for the interface. A narrow preview is a later milestone. |
| Windows support first | The lock layer, path behavior, and CI matrix need their own work. POSIX first is honest. |
| Copying a private history into a public repository | Old blobs, paths, and secrets are hard to audit. A fresh sanitized tree is smaller and reviewable. |
| A benchmark claim before running the benchmark | A claim without data is marketing. The honest status is "unrun". |

## What 1.0.0 keeps as seams

The 1.1 and 1.2 previews should not require a rewrite. 1.0.0 keeps these seams:

- The target is one lock module with `fcntl` behind it, so the 1.1 preview
  replaces the lock implementation, not the queue. In rc.1, `bin/tasks.py`
  still imports `fcntl` directly.
- `pathlib` and explicit path handling in the queue, doctor, installer, and
  tests. No POSIX-only shell assumption in the public contract.
- A documented agent and lane boundary: task ownership, provider concurrency,
  handoff, worktree, and merge ownership.
- Provider concurrency as policy, not a hardcoded number.
- State schema versioning so a later multi-agent change can migrate.

These are design constraints, not features. The previews still need their own
tests and release gates.

## Windows 1.1 preview

Planned scope:

- replace the direct `fcntl` use with a cross-platform lock module;
- keep the Markdown state format compatible;
- test the queue on Windows and POSIX;
- document the platform-specific install path;
- add a Windows CI job.

Not promised for 1.0.0. The current code imports `fcntl` directly in
`bin/tasks.py` and fails on native Windows Python. WSL2 may work but is not
tested.

## Multi-agent 1.2 preview

Planned scope is narrow:

- an explicit agent and lane boundary;
- one owner per task and per shared file;
- provider concurrency as policy;
- handoff and merge ownership;
- a state schema that can migrate.

It is not a general multi-agent framework. The queue and the review loop remain
the product. More agents do not create quality; independent review does.

## Portable lessons

These are the lessons worth carrying to another project:

- Keep mutable state out of the code tree.
- Make "done" require evidence, not a claim.
- Scale review to risk, not to ceremony.
- Make advisory review advisory, and measure it before trusting it.
- Prefer one reviewable diff to a large batch.
- Write the handoff before the context is gone.
- Delete a skill or option that does not pay for itself.
- Say "unrun" when you have not run it.

## Next

- [Concepts](concepts.md)
- [Workflow](workflow.md)
- [Jev calibration](jev-calibration.md)
