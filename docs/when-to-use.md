<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# When to use what

One rule: do trivial work directly; use the queue when the work must survive
the chat, needs review, or has more than one deliverable. If you are unsure,
run `/goal`; it routes the request.

## First action

| If you are about to... | Start with | What happens |
|---|---|---|
| Fix a typo, one-liner, or pure copy change | Just do it | No task, brief, or close needed |
| Start a nontrivial request | `/goal <request>` | It decides: one task, or a goal with children |
| Continue an existing task | `/brief <task-id>` | One-page brief with scope, acceptance, risks, and first check |
| Continue an existing goal | `/goal <goal-id>` | Finds the next ready child |
| Split independent work | `/goal` then `/lane <child-id>` | One worktree and owner per lane, then integrate |
| Stop and resume later | `/handoff <task-id>`, later `/takeover <task-id>` | Durable state transfer, not a transcript |
| Review a diff | `/review <task-id>` | Jev advisory first, independent challenge only when risk warrants |
| Merge reviewed lanes | `/integrate <task-id>...` | Ordered merge, full check, merged-diff review |
| Finish a task | `/close <task-id>` | Acceptance check, evidence, lesson, done transition |
| Review a UI | `/design-review` | Blocking, quick wins, and keep notes; no code edits |
| Prove real app behavior | `verification` skill | Generates a project-local `verify-<app>` recipe and proves it once |
| Inspect the queue | `/queue` | Ready tasks, board, or a specific packet |
| Clean up the workflow | `/tune` | Deletions first, then at most five evidence-backed patches |
| Check a goal plan before approval | `bin/jev_plan.py` | Completeness, testability, largest gap, and risk; advisory |

## Skills

| Skill | Use it when | Skip it when |
|---|---|---|
| `engineering-loop` | Nontrivial work: auth, secrets, data, external API, multi-file design, or "done" means production behavior | The change is a typo, one-liner, or pure copy edit |
| `goal` | The outcome spans sessions, has several deliverables, or should keep running unattended | The work is one reviewable diff; use the small-task path |
| `parallel-lanes` | Two or three independent slices with disjoint files or a fixed interface | The work touches one file, shared state, or needs one owner |
| `ui-design` | Layout, components, styling, visual review, or interface copy | The work is backend, data, or docs only |
| `verification` | You need proof against the real app and the project has no scripted way to drive it | A unit test, type check, lint, or direct command already proves the change |
| `work-queue` | Work must survive a session, needs ownership/dependencies/evidence, or runs in parallel | The work is trivial or a question that needs no change |

The detailed triggers and the 120-line budget are in [Skills](skills.md).

## Commands at a glance

Use **First action** when you know the intent. Use this table when you know the
command name and want its purpose.

| Command | Use it when | Result |
|---|---|---|
| `/goal` | You have a request, task id, or goal id and want the single entry point | Routes to a direct task or a reviewed goal plan |
| `/brief` | Before implementing, to pin scope and acceptance | Read-only one-page brief |
| `/queue` | You need to inspect, claim, block, or report queue state | Queue CLI output |
| `/lane` | A ready task needs an isolated branch and worktree | Worker packet for one lane |
| `/takeover` | You are resuming a paused or inherited task | Claims from the handoff and named files |
| `/review` | A diff exists and is ready for a verdict | Jev, optional devils-advocate, and a verdict |
| `/integrate` | Reviewed lanes must become one tree | Ordered merge, full check, merged review |
| `/close` | Acceptance and evidence are ready | Final review, lesson, done with evidence |
| `/handoff` | You are pausing, switching context, or near the context limit | Under-40-line handoff in the task |
| `/harvest` | Legacy: capture a lesson without a task or diff | One dated process-ledger entry |
| `/design-review` | A UI screenshot or reference needs a design pass | Blocking, quick wins, keep |
| `/tune` | After a work wave, to remove process weight | Deletions and up to five evidence-backed patches |

Every command's arguments are in [Command reference](command-reference.md).

## Agents

You rarely call these directly. The commands route to them.

| Agent | Use it when | Do not use it for |
|---|---|---|
| `explore` | You need read-only file and behavior tracing before a change | Implementation or design decisions |
| `implementer` | One bounded, mechanical, testable change is fully specified | Architecture, security policy, or open design |
| `integrator` | Reviewed lanes need an ordered merge with no conflicts | New feature work or conflict resolution by guesswork |
| `devils-advocate` | Jev flagged risk, the change touches auth/data/public API, or the operator asked for strict review | Routine low-risk diffs or a second author pass |

## Plugins

These run automatically. Use this table to decide whether to keep them on.

| Plugin | It helps when | Disable or ignore when |
|---|---|---|
| `auto-intake` | A nontrivial prompt should become an inbox task without retyping | You do not want prompt capture; set `AUTO_INTAKE=off` |
| `close-reminder` | A long session should remind you to close finished work | You dislike notifications or prompts; set `CLOSE_REMINDER_MODE=off` |
| `goal-watch` | An active `autorun` goal should continue after idle | You do not want unattended continuation; do not load it |
| `security-guard` | You want an advisory warning after a risky edit pattern | You do not want edit-time warnings; do not load it |

Environment and failure modes are in [Plugins](plugins.md).

## Jev

Jev is optional and advisory. A missing key is a skip, not a failed task.

| Use | When | Output |
|---|---|---|
| `jev_review.py` | A diff needs a typed second opinion before `/close` | Seven axis scores, ship/scope/tests/secret checks |
| `jev_plan.py` | A goal plan needs a completeness and risk check | Complete, testable, largest gap, risk, recommendation |
| `jev_triage.py` | `/close` is deciding whether a lesson is durable | Durable lesson, kind, scope, confidence |
| `--check` | Before a live Jev call | Model availability; exit 4 means the model is gone, so do not silently switch to a paid model |

Setup, exit codes, and privacy are in [Jev](jev.md).

## Queue CLI

Most operators use `/queue` or `/goal`; the CLI is the durable interface.

| You want to... | Command |
|---|---|
| Create one task | `tasks.py new` |
| Create a goal | `tasks.py goal` |
| Check one goal | `tasks.py goal-status` |
| List goals the watcher may continue | `tasks.py goals` |
| Validate or create a goal plan | `tasks.py plan` |
| Find work | `tasks.py list`, `tasks.py ready` |
| Read a task | `tasks.py show --packet` |
| Own a task | `tasks.py claim` |
| Move state or record evidence | `tasks.py status` |
| Pause | `tasks.py handoff` |
| Record one event | `tasks.py log` |
| Create a worktree lane | `tasks.py lane` |
| Clean a lane | `tasks.py remove-lane` |
| Check queue health | `tasks.py report`, `tasks.py validate` |
| Regenerate the board | `tasks.py board` |

Arguments are in [Command reference](command-reference.md).

## Common sequences

**One small task**

```text
/goal -> implement -> run checks -> /review -> /close
```

**Multi-step outcome**

```text
/goal -> review plan -> /goal go -> child loop -> /close goal
```

**Parallel work**

```text
/goal (plan children) -> /lane child A -> /lane child B
-> /review each -> /integrate -> /close lanes -> /close goal
```

**Pause and resume**

```text
/handoff <id> -> new session -> /takeover <id>
```

**UI change**

```text
ui-design skill -> implement -> /design-review -> /review -> /close
```

**Need proof the app works**

```text
verification skill -> generated verify-<app> -> run it -> /close with its output
```

## Other docs by need

| Need | Read |
|---|---|
| Install or upgrade | [Install](install.md) |
| First task walkthrough | [Quickstart](quickstart.md) |
| Definitions and state model | [Concepts](concepts.md) |
| Full loop and worked example | [Workflow](workflow.md) |
| A name for a rule | [Named principles](principles.md) |
| Benchmark a result | [Benchmark proof](benchmark-proof.md) |
| Choose a model | [Model routing](model-routing.md) |
| Evaluate a new skill | [Skill evaluation](skill-eval.md) |
| Calibrate Jev | [Jev calibration](jev-calibration.md) |
| Security and privacy | [Security and privacy](security-privacy.md) |
| Errors and fixes | [Troubleshooting](troubleshooting.md) |
| Why the design is this way | [Design notes](design-notes.md) |

## Do not use

- Do not run `/close` before the acceptance checks and evidence exist.
- Do not run `/tune` during feature work; it is a periodic cleanup turn.
- Do not run `/harvest` when a task exists; `/close` owns the lesson.
- Do not create a lane for shared files or one owner; serialize it instead.
- Do not run `devils-advocate` on a typo or a routine low-risk diff.
- Do not generate a verification skill when a direct test or command already
  proves the change.
- Do not run `/goal` for a typo; just fix it.
