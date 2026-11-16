<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# When to use what

One rule: do trivial work directly; use the queue when the work must survive
the chat, needs review, or has more than one deliverable. If you are unsure,
just describe the outcome; auto-intake creates the task and the harness routes
it. The commands below are manual forms for intervention.

## First action

| If you are about to... | Start with | What happens |
|---|---|---|
| Fix a typo, one-liner, or pure copy change | Just do it | No task, brief, or close needed |
| Start a nontrivial request | Just describe it | Auto-intake creates one task, and the harness runs brief, implement, verify, review, close, and ship. `/goal` is the manual form |
| Continue an existing task | `/brief <task-id>` | One-page brief with scope, acceptance, risks, and first check |
| Continue an existing goal | `/goal <goal-id>` | Finds the next ready child; `/goal` runs `goal-start` once |
| Split independent work | `/goal go` | Auto-lanes up to three ready children; `/lane` only for manual or existing-task isolation |
| Stop and resume later | `/handoff <task-id>`, later `/takeover <task-id>` | Durable state transfer, not a transcript |
| Review a diff | `/review <task-id>` | Jev advisory first, independent challenge only when risk warrants |
| Audit stateful code | `/state-audit <scope>` | Documents states, invariants, transitions, and a Mermaid statechart; fixes confirmed invalid paths |
| Finish a task or goal | Let the loop finish | The close step integrates lanes, reviews, reaps, records evidence, and ships. `/close` is the manual form |
| Review a UI | `/design-review` | Blocking, quick wins, and keep notes; no code edits |
| Prove real app behavior | `verification` skill | Create a `verify-<app>` recipe, maintain one, or formally check an invariant |
| Clean a codebase for agent input | `unslop` skill | Read-only audit, ratchet plan, and one-pattern fixes |
| Inspect the queue | `/queue` | Ready tasks, board, or a specific packet |
| Clean up the workflow | `/tune` | Deletions first, then at most five evidence-backed patches |
| Check a goal plan before approval | `bin/jev_plan.py` | Completeness, testability, largest gap, and risk; advisory |

## Skills

| Skill | Use it when | Skip it when |
|---|---|---|
| `engineering-loop` | Nontrivial work: auth, secrets, data, external API, multi-file design, or "done" means production behavior | The change is a typo, one-liner, or pure copy edit |
| `goal` | The outcome spans sessions, has several deliverables, or should keep running unattended | The work is one reviewable diff; use the small-task path |
| `parallel-lanes` | Two or three independent slices with disjoint files or a fixed interface | The work touches one file, shared state, or needs one owner |
| `state-audit` | Stateful code: queues, retries, locks, sessions, lifecycle, recovery, concurrency, or a stuck/duplicate/lost bug; the audit adds a Mermaid statechart | The change is stateless, a typo, or a pure copy/docs edit |
| `ui-design` | Layout, components, styling, visual review, or interface copy | The work is backend, data, or docs only |
| `unslop` | A codebase contains anti-patterns agents will copy; audit and ratchet them | The repo is a one-off script or has no repeated patterns |
| `verification` | You need to create or maintain proof against the real app, or formally check a property tests cannot reach | A unit test, type check, lint, or direct command already proves the change |
| `work-queue` | Work must survive a session, needs ownership/dependencies/evidence, or runs in parallel | The work is trivial or a question that needs no change |

The detailed triggers and the 120-line budget are in [Skills](skills.md).

## Commands at a glance

Use **First action** when you know the intent. Use this table when you know the
command name and want its purpose.

| Command | Use it when | Result |
|---|---|---|
| `/goal` | You want the manual form of the entry step, or have a task id, goal id, or request | Routes to a direct task or a reviewed goal plan; `go` creates lanes |
| `/brief` | Before implementing, to pin scope and acceptance | Read-only one-page brief |
| `/queue` | You need to inspect, claim, block, or report queue state | Queue CLI output |
| `/lane` | You need a manual worktree for an existing task; normal goals auto-lane | Worker packet for one lane |
| `/takeover` | You are resuming a paused or inherited task | Claims from the handoff and named files |
| `/review` | A diff exists and needs a check; this is not a finish step | Jev, optional devils-advocate, and a verdict |
| `/state-audit` | Stateful code needs its states, invariants, transitions, and statechart mapped, and confirmed invalid paths fixed | State-machine document with a Mermaid statechart, grouped findings, regression-tested fixes |
| `/close` | A task or goal is ready to finish; it integrates reviewed goals and reaps clean lanes | Final review, reap, lesson, done with evidence |
| `/handoff` | You are pausing, switching context, or near the context limit | Under-40-line handoff in the task |
| `/design-review` | A UI screenshot or reference needs a design pass | Blocking, quick wins, keep |
| `/tune` | After a work wave, to remove process weight; this is not a finish step | Deletions and up to five evidence-backed patches |

Every command's arguments are in [Command reference](command-reference.md).

## Command lifecycle

Think in five stages, not twelve commands:

- **Start or resume:** the auto-intake path. Manual forms are `/goal`, `/brief`,
  and `/takeover`; `/lane` is only for a worktree you deliberately want.
- **Check:** the review step (manual form `/review`) and
  `tasks.py goal-status`. A review is not a finish step.
- **Finish:** the close step (manual form `/close`) integrates goal lanes,
  reviews, reaps clean worktrees, records evidence, and ships. Unfinished
  children stop the close until they are finished.
- **Maintain:** `/tune` is periodic process cleanup, not a task finish.
- **Manual escape:** `/lane` only for an existing task or a worktree you
  deliberately want. `tasks.py reap` and `tasks.py remove-lane` are maintenance
  tools, not part of the normal finish path.

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
| `goal-watch` | An active goal is closable (reminder) or an autorun goal should continue | You do not want reminders or unattended continuation; do not load it |
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
| Start ready goal children in lanes | `tasks.py goal-start` |
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
/goal (plan children) -> /goal go (auto-lanes up to 3)
-> /review each -> /close goal (integrates reviewed lanes)
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
verification skill -> create, maintain, or formal mode -> proof artifact -> /close
```

**Stateful change**

```text
/state-audit <scope> -> docs/state-machines.md with Mermaid statechart -> grouped fixes
-> regression tests -> /review -> /close
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
- Do not close a goal with active children; finish them first.
- Do not use `/lane` for a normal goal; `/goal go` auto-lanes.
- Do not run `/tune` during feature work; it is a periodic cleanup turn.
- Do not create a lane for shared files or one owner; serialize it instead.
- Do not run `devils-advocate` on a typo or a routine low-risk diff.
- Do not generate a verification skill when a direct test or command already
  proves the change.
- Do not run `/state-audit` on stateless code or use it to justify a redesign.
- Do not run `/goal` for a typo; just fix it.
