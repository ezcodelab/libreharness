<!-- SPDX-License-Identifier: MIT -->
# Agent rules

## Absolute constraints
- Never commit, log, print, or embed secrets, tokens, API keys, production
  credentials, or PII.
- Never mutate production systems, live data, shared infrastructure, or billing
  accounts without explicit human approval in the current turn.
- Never force-push, rewrite shared git history, or push directly to `main` or
  `master`.
- Prefer the smallest complete change. Do not expand scope or improve unrelated
  code.
- When a task asks to replace specific values in existing files, use targeted
  string replacement and preserve every other byte. Replace only the value
  itself; do not rewrite the containing line, embedded diff, or file structure.
  Do not reformat, reserialize, quote, or reflow unrelated content. Check
  `git diff` before finishing.
- When a task names the files or acceptance set to change, do not edit outside
  it. If you find a related issue outside that set, report it; the task owner
  decides whether to widen the scope.
- Do not claim a test, build, lint, or check passed unless you ran it and saw
  the result.
- If requirements are ambiguous or a decision is hard to reverse, ask before
  acting.

## Task scale
- **Trivial** (typo, one-liner, pure copy): make the change, quick check, done.
- **Nontrivial** (external API, secrets or auth, schema or data model,
  multi-file design, security tradeoff, or production behavior): load the
  `engineering-loop` skill and follow it.
- Read the project `AGENTS.md` and `docs/process-lessons.md` before significant
  changes. Keep facts, assumptions, and open verification items distinct.
- A completed task appends one dated entry to the project's
  `docs/process-lessons.md`: Surprise, Cost, Rule, Doc updated, and
  `Promote-to-global` when portable. "None" is a valid Surprise.

## Work intake and ownership
- The durable unit is a task under `$HARNESS_STATE/work/tasks`. Use `/goal` for
  any task, small or large; it executes a single task directly or plans a
  multi-step one.
- For a multi-deliverable outcome, `/goal` plans first, then `/goal go` creates
  and executes the validated plan. `/goal go --unattended` enables the per-goal
  watcher. A goal is done only when every child is final and its acceptance is
  checked.
- Read the task packet before coding: scope, out of scope, acceptance,
  dependencies, context, evidence, handoff.
- One task, one owner, one reviewable diff. Do not claim a task with open
  dependencies unless the operator accepts the risk.
- If work changes scope or acceptance, update the task before editing code.
- A task is `done` only with evidence: a command and result, a measured check,
  or an explicit `[T]` with a plan.

## Context and handoff
- Load in this order: task packet and handoff; project `AGENTS.md`,
  `docs/process-lessons.md`, and `docs/README.md`; the named source and tests; at
  most three matching lessons and one matching skill.
- Do not read the whole state directory, the whole lesson ledger, a full
  transcript, or unrelated projects. Prefer indexes and `rg`.
- At a phase boundary, before a model switch, or around 60% context, run
  `/handoff`. Do not carry a finished phase's tool output forward.
- Keep transient task state in the task file; keep durable project rules in the
  repo; keep cross-project rules in the state directory.
- No secrets, token values, or production data in a task, handoff, lesson, or
  log.

## Parallel work
- Parallelize only independent slices with disjoint files or a fixed interface,
  a testable acceptance, and review capacity. Cap at two or three lanes.
- Write the ownership map first: lane, task, files or interfaces,
  branch/worktree, dependencies, merge order.
- Shared files get one owner. Lanes do not edit another lane's files or push.
- One integrator merges in the declared order, resolves conflicts, and reruns
  the full check. A green lane is not a green integration.

## Named principles
Use these names to steer a decision. When one applies, name the principle and
the decision it changed. The long form with examples is in `docs/principles.md`
in the repository.

- **Attack the premise.** When two fixes that share a premise fail the same
  gate, write the premise down and test it before a third fix.
- **Prove it works.** Check the real artifact, not a proxy, a self-report, or
  "it compiles."
- **Sequence verifiable units.** End each small unit in a check before starting
  the next; keep one task to one reviewable diff.
- **Explain the number.** Name the limiter and rule out errors, skipped work,
  untuned sides, and noise before reporting a measurement.
- **Guard the context window.** Route bulk reading to subagents, keep summaries
  in the main thread, and hand off before context is exhausted.
- **Separate before serializing shared state.** Give parallel work disjoint
  files or worktrees; add coordination only for a real invariant.
- **Subtract before you add.** Delete dead weight and speculative abstractions
  before building the smallest complete change.
- **Encode lessons in structure.** After the same correction twice, fix it with
  architecture, types, lint, or a test; docs last.

## Decision authority
- **Two-way doors** (easy to reverse): decide and act.
- **One-way doors** (data models, migrations, auth boundaries, public API
  contracts, infrastructure, CI/CD, tenancy, major dependencies, publication):
  stop, explain why it is one-way, list at least two alternatives with
  tradeoffs, and ask before committing.

## Verification and review
- Define done as runnable checks. Run them and report actual results.
- Run `/review` before declaring nontrivial work complete. The merged tree gets
  the final review.
- Stateful changes: when a change adds or alters a state machine, retry, lock,
  concurrency, session, queue, or lifecycle path, run the `state-audit` skill
  and update the project's `docs/state-machines.md` before `/review`. A
  confirmed invalid transition gets a regression test before the fix.
- Prefer independent review for nontrivial changes. If no review ran, say so.
- When a failure pattern appears twice, encode it as a test, lint rule, or
  instruction.

## Completion report
- **Substantial:** Gate, Done, Evidence, Lessons, Deferred, Stopped because.
- **Routine nontrivial:** what changed, what was run, what remains unproven.
- **Trivial:** one line; say "not run" when nothing was checked.
