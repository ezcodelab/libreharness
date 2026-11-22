<!-- SPDX-License-Identifier: MIT -->

# Reference

LibreHarness is a durable work queue and a risk-scaled engineering workflow for
OpenCode. It ships as a plugin: commands, agents, skills, and two small local
plugins load from the package.

## Requirements

- Linux.
- OpenCode 2.x.
- Node 20 or newer.
- Python 3.10 or newer.
- A model provider of your choice.

Jev is optional. The queue and the test suite work without a key.

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
permissions. Add a model to a stub for per-agent routing.

From a checkout, use the absolute path instead of the npm name:

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
| `HARNESS_STATE` | Mutable local data | tasks, board, lock, metrics, optional Jev key file |

With the plugin, `HARNESS_HOME` is the package root and OpenCode configuration
stays in `~/.config/opencode`. No runtime component writes into
`HARNESS_HOME`; state survives an upgrade.

```text
$HARNESS_STATE/
├── work/
│   ├── tasks/<yyyy-mm-dd>-<slug>.md
│   ├── BOARD.md
│   └── .lock
└── metrics/workflow-log.csv
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
| `autorun`, `max_continuations` | Per-goal continuation policy |
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
python3 "$HARNESS_HOME/bin/tasks.py" claim "$ID" --owner quickstart
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" review --note "quickstart"
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" done \
  --evidence "python3 $HARNESS_HOME/bin/tasks.py board: task listed"
python3 "$HARNESS_HOME/bin/tasks.py" board
```

A tracked deferral is `[T]` plus a plan and what would change it. It is not a
pass.

### Goal

A goal is an umbrella task with `kind: goal`, child tasks, and its own scope and
acceptance. It is done only when every child is final and its acceptance is
checked. The plan validator checks child scope and acceptance, dependency
cycles, `owns` overlap, and lane assignment.

### Lane

A lane is one branch and worktree for one task, so independent slices do not
edit the same files. A lane record has the task, branch, base, worktree, owner,
and owned paths. Cap parallel lanes at two or three, give shared files one
owner, and let one integrator merge in the declared order and rerun the full
check. A green lane is not a green integration.

### Handoff

A handoff is a bounded state transfer for the next session: state, decisions,
changed files, the exact next action, and any open verification. Put it in the
task's Handoff section, not in a transcript.

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
deterministic checks -> verification artifact
  |
  v
review -> close -> ready PR -> CI + independent verifier PASS
  |
  v
merge only the verified patch -> post-merge check
```

No slash command is required. `/goal`, `/brief`, `/review`, `/close`, and
`/lane` are escape hatches for a human who wants to intervene.

1. **Intake.** A nontrivial request becomes one `inbox` task. A trivial request
   is done directly. A request with several deliverables becomes a goal with
   two to six children. Confirm scope and observable acceptance before
   claiming; ask one question if the request is ambiguous.
2. **Brief.** Read the packet, project rules, and only the named source and
   tests. List invariants, risks, unknowns, the first action, and the exact check
   that proves it.
3. **Implement.** Keep one reviewable diff. Update the task before a scope
   change. Use the smallest complete change.
4. **Prove.** Run the acceptance checks and record the command and result.
5. **Review.** Run `/review`. Jev is advisory; `devils-advocate` is the
   independent fallback. Only a confirmed P0/P1 blocks.
6. **Close.** Integrate lanes, run the final review on the merged tree, reap
   clean worktrees, write one lesson, record evidence, and ship through a ready
   PR. No path is protected; a ready PR with green checks and a recorded verdict
   auto-merges. An irreversible deploy, data deletion, or force-push still stops.

## Commands

| Command | Use |
|---|---|
| `/goal <request-or-id>` | Plan or resume a task or goal |
| `/brief <id>` | Build a one-page brief |
| `/queue` | Inspect the board and ready work |
| `/lane <id>` | Create a manual worktree lane |
| `/takeover <id>` | Resume a task from its packet |
| `/review <id>` | Tiered review of the working diff |
| `/state-audit <path>` | Document and check a state machine |
| `/close <id>` | Integrate, review, reap, lesson, evidence, ship |
| `/handoff` | Write a bounded handoff |
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

## Skills

| Skill | Use |
|---|---|
| `engineering-loop` | Entry point and playbook router for non-trivial work |
| `goal` | Multi-deliverable goal planning and execution |
| `parallel-lanes` | Two or three independent lanes |
| `shipping` | Ready PR, CI, independent verdict, merge |
| `state-audit` | States, invariants, transitions, regression tests |
| `ui-design` | UI and UX work |
| `unslop` | Prose only: replies, PR bodies, docs, commit messages |
| `no-comments` | Remove comment alibis before review |
| `correct` | Repeated mistake classes become checks |
| `verification` | Prove real app behavior |
| `work-queue` | Durable tasks with scope, acceptance, and evidence |

`engineering-loop` maps a request to `investigation`, `bug-fix`, `feature`,
`refactoring`, `perf`, `hillclimb`, `autonomous-multiphase`, or `correct`. The
checklists live in `skills/engineering-loop/references/playbooks.md`. Per-rule
encodings live in `skills/correct/references/rule-ledger.md`.

## Agents

| Agent | Role |
|---|---|
| `explore` | Read-only repository scout |
| `implementer` | One scoped, testable implementation |
| `integrator` | Bounded merge in a declared order |
| `devils-advocate` | Independent read-only review |

## Plugins

Two local plugins are bundled. They use Node built-ins and never call a model.

- **auto-intake** turns a nontrivial prompt into one inbox task and appends a
  queue note. It skips questions, delegation prompts, and secret-shaped text.
  Opt out with `AUTO_INTAKE=off`.
- **goal-watch** reminds once per session when an active goal is closable, and
  continues one `autorun` goal while it has ready children. It never creates,
  closes, or marks work done.

Protect secret files in one layer rather than in every agent: install
`envsitter-guard` or `cc-safety-net`, or add a global `read *.env ask` rule.

## Jev

Jev is an advisory typed-question client. It sends one request and prints one
structured answer. It never merges, closes, or blocks work by itself.

| Client | Use | Input |
|---|---|---|
| `bin/jev_review.py` | Typed second opinion on a diff | Task and diff |
| `bin/jev_plan.py` | Completeness and risk check on a goal plan | Goal and children |
| `bin/jev_triage.py` | Decide whether a close lesson is durable | Compact close state |

Configuration:

| Variable | Required | Meaning |
|---|---|---|
| `JEV_MODEL` | Yes for a live call | Model id; no hardcoded default |
| `JEV_ENDPOINT` | No | Typed-question endpoint |
| `JEV_API_KEY` | No | Key from the environment |
| `JEV_KEY_FILE` | No | Path to a mode 600 key file |

The key resolver checks `--key-file`, `JEV_API_KEY`, `OPENCODE_API_KEY`,
`TYPESAFE_API_KEY`, `JEV_KEY_FILE`, then `~/.config/opencode/jev.key`. Use one
source. A missing key is a skip at the workflow level and exit 3 from a
standalone client.

Exit codes:

| Exit | Meaning |
|---|---|
| 0 | Pass or result produced |
| 2 | Review send-back |
| 3 | Configuration, API, missing key, or secret-shaped input |
| 4 | Requested model is gone; do not silently switch to a paid model |

Set the model and check availability:

```sh
export JEV_MODEL="<model-id>"
python3 "$HARNESS_HOME/bin/jev_review.py" --check
```

A review sends the task and diff, truncated at `--max-chars` (default 30000), to
the configured endpoint. It refuses secret-shaped input unless
`--allow-secret-shaped` is passed for a reviewed exception. The endpoint receives
only that material and the key.

## Security and privacy

- Task files, the board, metrics, and Jev key files live under
  `$HARNESS_STATE`. The directory is mode 700; use disk encryption if the work is
  sensitive.
- `auto-intake` refuses to store a prompt that matches its secret patterns and
  redacts secret-shaped and PII-shaped text in titles.
- The Jev review and plan clients reject secret-shaped input.
- The queue does not encrypt task files.
- Nothing here sends telemetry. Jev sends a request only when a command runs it.

Report a vulnerability through the private advisory form at
<https://github.com/ezcodelab/libreharness/security/advisories/new>. Do not put a
live key in an issue.

## Shipping and CI

Public repositories use GitHub as canonical and Gitea as a read-only mirror.
Open a ready PR, wait for the required checks, obtain an independent verdict on
the exact head, then merge that head:

```sh
HEAD=$(gh pr view <number> --json headRefOid --jq .headRefOid)
gh pr checks <number> --watch --required --interval 20
gh pr merge <number> --squash --match-head-commit "$HEAD" --delete-branch
```

A change to a gate, CI, auth, deploy, or release path stops at merge-ready and
waits for the operator. Ask once in the same turn with the exact
`--admin --match-head-commit` command. If authorized, merge that head; if
declined, close the PR with the reason. Never leave a reviewed PR open.

Never push to `main` or force-push a shared branch.

The repository checks are native tools:

| Check | Command |
|---|---|
| Python tests | `python3 -m unittest discover -s tests -p 'test_*.py' -v` |
| Node tests | `npm run test:node` |
| Package contents | `npm pack --dry-run` |
| Markdown correctness | `npx --yes markdownlint-cli2@0.18.1 '**/*.md'` |
| Links | `lychee --offline --include-fragments '**/*.md'` |
| Secrets | `gitleaks detect --source . --config .gitleaks.toml` |
| Shell | `shellcheck -x` |
| Workflows | `actionlint` |

Release: bump `package.json`, add a `CHANGELOG.md` entry, tag `v<version>`, and
let `.github/workflows/release.yml` publish the npm package and GitHub release.

## License

All code, documentation, and snippets are MIT. See `LICENSE` and `NOTICE`.
