<!-- SPDX-License-Identifier: MIT -->

# Reference

LibreHarness is a durable work queue and a risk-scaled engineering workflow for
OpenCode. It ships as a plugin: commands, agents, skills, and two small local
plugins load from the package.

## Requirements

- Linux.
- OpenCode 2.x.
- [Node 20 or newer](https://nodejs.org/en/download).
- [Python 3.10 or newer](https://www.python.org/downloads/).
- [Git](https://git-scm.com/downloads) for the work queue and review artifacts.
- [GitHub CLI](https://cli.github.com/), authenticated, to ship pull requests.
- A model provider of your choice.

## Install

Add the package to the global `plugins` array in
`~/.config/opencode/opencode.json`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["libreharness@2.0.0"],
  "agents": {
    "devils-advocate": {},
    "explore": {},
    "implementer": {},
    "integrator": {}
  }
}
```

The four agent stubs are required. The plugin API can update an existing agent
but cannot create one; the plugin fills each stub's prompt, mode, and
permissions. Add a model to a stub for per-agent routing, or pass
`options.agentModels` with entries such as
`"explore": "<provider>/<model>#<variant>"`. The plugin validates the reference
and changes only the fresh child agent's model.

OpenCode loads global and project `AGENTS.md` files natively. The plugin registers
no instruction-injection hook, so the LibreHarness contract stays scoped to this
workspace.

From a checkout or extracted GitHub release archive, install the runtime
dependency and use the absolute path instead of the npm name:

```sh
npm install --omit=dev --no-audit --no-fund
```

```jsonc
"plugins": ["/path/to/libreharness"]
```

The state directory defaults to `~/.local/state/libreharness`, created with mode
700. Override it with an options object:

```jsonc
"plugins": [
  { "package": "libreharness@2.0.0", "options": { "state": "/your/state" } }
]
```

Upgrade by changing the version and reloading OpenCode. No files are copied into
the config directory.

## Two roots

| Root | Meaning | Examples |
|---|---|---|
| `HARNESS_HOME` | Code and configuration | `bin/tasks.py`, `commands/`, `skills/`, `plugins/` |
| `HARNESS_STATE` | Mutable local data | tasks, board, lock, metrics, review artifacts |

With the plugin, `HARNESS_HOME` is the package root and OpenCode configuration
stays in `~/.config/opencode`. No runtime component writes into
`HARNESS_HOME`; state survives an upgrade.

```text
$HARNESS_STATE/
├── work/
│   ├── tasks/<yyyy-mm-dd>-<slug>.md
│   ├── reviews/<task-id>.json
│   ├── BOARD.md
│   └── .lock
└── metrics/
    ├── workflow-log.csv
    ├── session-tasks.jsonl
    └── usage-log.jsonl
```

`BOARD.md` is generated. Edit task files, not the board.

## Task

A task is one Markdown file. It should fit one agent session and one reviewable
diff.

Frontmatter fields:

| Field | Meaning |
|---|---|
| `id` | Date-based id; must match the file name |
| `title` | Human title |
| `project` | Project label, default `general` |
| `kind` | `task` or `goal` |
| `status` | One of the status values below |
| `priority` | 0 to 4; lower is more urgent |
| `owner` | Session, person, or lane that claimed it |
| `parent` | Goal id for a child task |
| `session` | Optional session id for the continuation watcher |
| `lane` | Optional lane name |
| `owns` | Comma-separated repo-relative paths this task may change |
| `branch`, `worktree`, `base` | Lane isolation fields |
| `depends_on` | Comma-separated task ids that must finish first |
| `reviewer` | Optional reviewer label |
| `autorun`, `max_continuations` | Optional per-goal continuation cap; the default stops when progress stalls |
| `blocked_reason` | Why a task is blocked |
| `created`, `updated` | Dates |
| `tags` | Comma-separated labels |

The body has these sections: Scope, Out of scope, Acceptance, Context, Plan,
Evidence, Handoff, Log.

### Status

| Status | Meaning |
|---|---|
| `inbox` | Captured, not shaped. Auto-intake creates these. |
| `ready` | Has scope and acceptance, no open dependency, claimable |
| `active` | Claimed by one owner and being worked |
| `blocked` | Waiting on a decision, dependency, or external fact |
| `review` | Ready for review or integration |
| `done` | Final, with evidence |
| `abandoned` | Final, deliberately not done |

`done` and `abandoned` are final. A task cannot jump from `inbox` or `ready` to
`done`; it must be claimed and checked first.

### Acceptance and evidence

Acceptance is an observable check: a command, a test, a measured value, or a
concrete behavior. Evidence is the result that proves it. The queue rejects
`none`, `n/a`, `na`, `tbd`, `ok`, `pass`, `done`, `tests pass`, and empty
evidence.

```sh
ID=$(python3 "$HARNESS_HOME/bin/tasks.py" new "Try LibreHarness" \
  --project demo \
  --scope "Create and close one task." \
  --acceptance "- board lists the task")
# Write exactly one Data shape: line and one Verify: line into ## Plan,
# for example with /brief, before claim.
python3 "$HARNESS_HOME/bin/tasks.py" claim "$ID" --owner quickstart
python3 "$HARNESS_HOME/bin/tasks.py" review "$ID" --repo "$PWD" \
  --run "python3 -m unittest tests.test_tasks -v"
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" review --note "review passed"
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" done \
  --evidence "python3 $HARNESS_HOME/bin/tasks.py board: task listed"
python3 "$HARNESS_HOME/bin/tasks.py" board
```

A tracked deferral is `[T]` plus a plan and what would change it. It is not a
pass.

### Claim contract

Before claim, the task `## Plan` must carry exactly one `Data shape:` line and
one `Verify:` line.

- `Data shape` is a non-empty JSON object or array on one line, or
  `path <repo-relative-file>#<symbol>` where the file declares the symbol, or
  `none - <reason>` only for a task tagged `docs` or `chore`.
- `Verify` is one command from the review allowlist: `npm test`,
  `npm run test:*`, `npm run lint:*`, `node tests/*.test.mjs`,
  `python3 -m unittest ...`, `pytest ...`, `ruff check ...`, `make check`,
  `cargo test`, `go test ./...`, `npx --no-install markdownlint-cli2 ...`, or the
  project-local verification smoke script.

A product task that cannot name its real check stops unverified instead of
pointing Verify at an unrelated harness check.

### Review artifact

`tasks.py review <id> --repo <repo> --run "<command>"` runs allowlisted argv
without a shell, records the observed exits, the exact HEAD, a digest of the
reviewed diff, and a digest of Scope, Out of scope, Acceptance, Data shape, and
Verify in `work/reviews/<id>.json`, then validates the artifact. No-argument
mode validates an existing artifact; `--unverify` downgrades it. Any commit,
working-tree change, or task contract change makes the artifact stale.

PASS needs at least one check, every recorded exit zero, and the task's Verify
command exactly once. A missing, malformed, stale, failed, or task-mismatched
artifact blocks `status <id> review`, `status <id> done`, `/close`, and shipping.

### Goal

A goal is an umbrella task with `kind: goal`, child tasks, and its own scope and
acceptance. It is done only when every child is final and its acceptance is
checked. The plan validator checks child scope and acceptance, dependency
cycles, `owns` overlap, and lane assignment.

### Lane

A lane is one branch and worktree for one task, so independent slices do not
edit the same files. A lane record has the task, branch, base, worktree, owner,
and owned paths. Add lanes only for disjoint owned paths and when one integrator
can merge them in the declared order; give shared files one owner and rerun the
full check after integration. A green lane is not a green integration.

### Handoff

A handoff is a bounded state transfer for the next session. The Handoff section
requires seven labels: State, Decisions, Files, Checks, Open, Next, and Context.
`tasks.py handoff <id>` rejects an incomplete handoff and
`tasks.py handoff <id> --check` validates an existing one. The packet carries
the handoff together with scope, acceptance, plan, and evidence.

## Workflow

```text
request
  |
  v
auto-intake task (inbox)
  |
  v
goal/work-queue brief -> claim or lane -> implement
  |
  v
deterministic checks -> review artifact
  |
  v
review -> close -> ready PR -> CI -> merge only the reviewed head
  |
  v
post-merge check
```

No slash command is required. `/goal`, `/brief`, `/review`, `/close`, and
`/lane` are escape hatches for a human who wants to intervene.

1. **Intake.** A nontrivial request becomes one `inbox` task. A trivial request
   is done directly. A request with several deliverables becomes a goal with
   multiple children. Confirm scope and observable acceptance before
   claiming; ask one question if the request is ambiguous.
2. **Brief.** Read the packet, project rules, and only the named source and
   tests. List invariants, risks, unknowns, the first action, and the exact check
   that proves it.
3. **Implement.** Keep one reviewable diff. Update the task before a scope
   change. Use the smallest complete change.
4. **Prove.** Run the acceptance checks and record the command and result.
5. **Review.** Run the task's Verify command and focused deterministic checks
   through `tasks.py review --run`. Record the observed exits and HEAD, then
   inspect comments, reach, and state impact. The default path makes no model
   call. A second opinion is an explicit operator request and cannot create a
   PASS. A green artifact is not proof: run the acceptance check on the real
   artifact.
6. **Close.** Integrate lanes, validate the review artifact on the merged tree,
   reap clean worktrees, record evidence, and ship through a ready PR. No path is
   protected; a ready PR with green required checks and a PASS artifact at the
   exact head auto-merges. An irreversible deploy, data deletion, or force-push
   still stops.

## Commands

| Command | Use |
|---|---|
| `/goal <request-or-id>` | Plan or resume a task or goal |
| `/brief <id>` | Build a one-page brief |
| `/queue` | Inspect the board and ready work |
| `/lane <id>` | Create a manual worktree lane |
| `/takeover <id>` | Resume a task from its packet |
| `/review <id>` | Deterministic review with a recorded artifact |
| `/state-audit <path>` | Document and check a state machine |
| `/close <id>` | Integrate, validate the artifact, reap, evidence, ship |
| `/handoff` | Write a bounded handoff |
| `/unslop-ui <surface>` | Baseline, two variants, one A/B choice, implement, verify, close, ship |
| `/design-review` | Review UI work |
| `/tune` | Propose deletions and process patches |

### Queue CLI

Run `python3 "$HARNESS_HOME/bin/tasks.py" <command>`.

| Command | Purpose |
|---|---|
| `new` | Create a task |
| `goal` | Create a goal |
| `plan --file <json>` | Validate and create a goal plan |
| `claim` | Claim a task, optionally with a branch and worktree |
| `review` | Record or validate the review artifact for one task |
| `status` | Change status, add a note or evidence |
| `lane` | Create a worktree lane |
| `remove-lane` | Remove a lane |
| `reap` | Remove clean worktrees whose branch is merged |
| `list`, `ready`, `goals` | Inspect work |
| `show` | Show a task or its packet |
| `handoff` | Write a handoff |
| `log` | Append a log line |
| `goal-start`, `goal-status` | Start or inspect a goal |
| `report`, `board`, `validate` | Metrics, generated board, and validation |

`bin/usage_report.py` joins the local usage ledger to completed tasks. Its
`cost_per_verified_task` divides all measured model cost, including failed and
abandoned work, by the number of tasks with a PASS review artifact. Run
`python3 "$HARNESS_HOME/bin/usage_report.py" --json`.

## Skills

The map lives in [skills/README.md](../skills/README.md).

`engineering-loop` maps a request to `investigation`, `bug-fix`, `feature`,
`refactoring`, `perf`, `hillclimb`, `autonomous-multiphase`, or `correct`. The
index lives in `skills/engineering-loop/references/playbooks.md`; only the
selected checklist under `references/playbooks/<id>.md` is loaded. Per-rule
encodings live in `skills/correct/references/rule-ledger.md`.

## Agents

| Agent | Role |
|---|---|
| `explore` | Read-only repository scout |
| `implementer` | One scoped, testable implementation |
| `integrator` | Bounded merge in a declared order |
| `devils-advocate` | Independent read-only review |

Per-agent routing is configuration, not an ambient model call. A normal setup
uses a cheap workhorse for `explore`, routine `implementer` work, and
`integrator`, while reserving a stronger planner or challenger model for
ambiguous design, security, state/concurrency, repeated failure, and an
operator-requested second opinion. The main session keeps the operator's chosen
model.

## Plugins

Three local plugins are bundled. They use Node built-ins and never call a model.

- **auto-intake** turns a nontrivial prompt into one inbox task and appends a
  queue note. It skips questions, delegation prompts, and secret-shaped text.
  Opt out with `AUTO_INTAKE=off`.
- **goal-watch** reminds the owning session once when an active goal is closable,
  and continues one `autorun` goal while it has ready children. When progress
  stalls or the continuation budget is exhausted, it sends one stop notice that
  requires a handoff. It never creates, closes, or marks work done.
- **usage-ledger** records provider-reported cost, token classes, model steps,
  and retries per session. It stores no prompts, diffs, or model output. Opt out
  with `USAGE_LEDGER=off`.

Protect secret files in one layer rather than in every agent: install
`envsitter-guard` or `cc-safety-net`, or add a global `read *.env ask` rule.

## Security and privacy

- Task files, the board, metrics, and review artifacts live under
  `$HARNESS_STATE`. The directory is mode 700; use disk encryption if the work is
  sensitive.
- `auto-intake` refuses to store a prompt that matches its secret patterns and
  redacts secret-shaped and PII-shaped text in titles.
- Review checks run local commands and record their exits; the artifact contains
  no secret material beyond what a command prints.
- The queue does not encrypt task files.
- The usage ledger is local and contains no prompts, diffs, or model output.
  Nothing here sends usage data off the machine.

Report a vulnerability through the private advisory form at
<https://github.com/ezcodelab/libreharness/security/advisories/new>. Do not put a
live key in an issue.

## Shipping and CI

Public repositories use GitHub as canonical and Gitea as a read-only mirror.
One task gets one small, logically separated PR with a `type(scope): subject`
title and the required body headings. Keep it reviewable in one sitting; split
by review boundary, not an arbitrary number. Independent tasks open separate
PRs off trunk. Only dependent follow-ups stack, and a stack lands bottom-up.

Validate the review artifact on the head that will land, check the local PR
contract, then stay through required checks and merge that exact head:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" review <id> --repo "$PWD"
python3 "$HARNESS_HOME/bin/pr_guard.py" check --base main \
  --title "type(scope): subject" --body-file /tmp/opencode/pr-body.md
HEAD=$(gh pr view <number> --json headRefOid --jq .headRefOid)
python3 "$HARNESS_HOME/bin/pr_guard.py" land \
  --pr <number> --head "$HEAD" --base main
```

A missing, stale, failed, or UNVERIFIED artifact, a malformed PR, a pending or
failed required check, a conflict, a draft, or a secret in the diff stops the
merge. The check wait is bounded to five minutes and accepts a terminal
successful conclusion even when GitHub leaves the check-run status stale. A
failed or stalled check stops with its name and state instead of waiting for the
workflow timeout. Fix CI, rebase only the PR's own branch, or close a superseded
PR. Do not leave a ready PR open for the operator to finish. A repository human
gate, such as required reviews or a ruleset, also stops it until satisfied. Do
not replace that gate with a model verdict.

Never push to `main` or force-push a shared branch. A force-with-lease push is
allowed only on the PR branch you own, after a rebase, followed by a new review
artifact.

Repository checks use pinned tools fetched by npm:

| Check | Command |
|---|---|
| Full local set | `npm run check:local` |
| Download pinned tools | `npm run tools:install` |
| Syntax | `npm run check:syntax` |
| Python tests | `python3 -m unittest discover -s tests -p 'test_*.py' -v` |
| Node tests | `npm run test:node` |
| Comment debt | `npm run lint:comments` |
| Package contents | `npm pack --dry-run` |
| Markdown correctness | `npm run lint:md` |
| Links | `npm run lint:links` |
| Secrets | `npm run lint:secrets` |
| Shell | `npm run lint:shell` |
| Workflows | `npm run lint:workflows` |

The check scripts download checksum-verified lychee, gitleaks, actionlint, and
shellcheck into `$XDG_CACHE_HOME/libreharness/tools` for Linux x64 and arm64.
They do not change the plugin runtime or its install size. CI calls the same
commands.

A task's Verify command may use its own project tools such as pytest, Ruff,
Cargo, Go, Make, or npm scripts. Those belong to the target project; LibreHarness
does not bundle or install them. Git and the authenticated GitHub CLI are the
only non-language runtime commands the harness calls itself.

Release: bump `package.json`, add a `CHANGELOG.md` entry, tag `v<version>`, and
let `.github/workflows/release.yml` publish the npm package and GitHub release.

## License

All code, documentation, and snippets are MIT. See `LICENSE` and `NOTICE`.
