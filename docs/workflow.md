<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Workflow

The harness is a loop, not a ceremony. A trivial change can skip the queue. A
change that needs memory, review, or more than one session uses the loop.

## The loop

```text
request
  |
  v
/goal  --->  one reviewable diff?  --- yes --->  task (ready)
  |                    |
  |                    no
  |                    v
  |               plan (children, lanes, owns, deps)
  |                    |
  |                    v
  |                  /goal go
  v                    |
/brief <----------------+
  |
  v
claim or /lane
  |
  v
implement
  |
  v
run checks  --->  evidence, or [T] with a plan
  |
  v
/review  --->  Jev advisory + optional independent challenge
  |
  v
/close  --->  final review, optional Jev triage, one lesson, done with evidence
  |
  v
/integrate (when lanes exist)
```

## 1. Intake

`/goal` is the single entry. It accepts a request, an existing task id, an
existing goal id, or the `go` subcommand.

- A trivial request is done directly and does not enter the queue.
- A request that is one reviewable diff becomes one task.
- A request with several deliverables becomes a goal with two to six children.

The intake step should produce a scope and an observable acceptance. If the
request is ambiguous, ask one question. Do not invent acceptance.

Auto-intake may create an `inbox` task from a nontrivial prompt. Use that task;
do not create a duplicate. Confirm scope and acceptance before claiming.

## 2. Brief

`/brief <id>` builds a one-page brief:

- task and scope;
- out of scope;
- acceptance as observable checks;
- invariants and trust boundaries;
- risks and unknowns;
- definition of done;
- zero to three relevant past lessons;
- first action and the exact check that proves it.

The brief is read-only. It does not edit code.

## 3. Claim or lane

For one task:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" claim "$ID" --owner "$SESSION"
```

Claiming checks open dependencies and branch or worktree ownership. If another
owner holds the task, stop. If a dependency is open, stop unless the operator
accepts the risk and you record why.

For parallel work:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" lane "$ID" \
  --repo "$REPO" --owner lane-a
```

Write the ownership map first: lane, task, files or interfaces, branch,
worktree, dependency, and merge order. Cap at two or three lanes. Shared files
get one owner.

## 4. Implement

Load the task packet, the project rules, and the files the task names. Do not
read the whole repository.

Keep the change to one reviewable diff. If the scope changes, update the task
before editing code. A silent scope change is a defect.

Use the smallest complete change. Do not add an abstraction, option, or
dependency nobody asked for. Keep validation at trust boundaries and error
handling that prevents data loss.

## 5. Prove

Run the checks named in acceptance. Record the command and the result:

```text
python3 -m unittest discover -s tests -p 'test_*.py': OK
node tests/security-guard.test.mjs: PASS
```

If a check cannot run, record `[T]` with a plan and what would change it. A
placeholder is not evidence. The queue rejects `none`, `ok`, `pass`, `done`,
and `tests pass` for a done transition.

The evidence gate exists because "the model said it passed" is not a result.
It is enforced in `bin/tasks.py`, so it applies whether a person or an agent
closes the task.

## 6. Review

`/review <id>` saves the diff, checks whether Jev is available, and runs the
tiered review:

1. Jev preflight with `--check`.
2. Jev review, if available.
3. `devils-advocate` only when risk warrants it.
4. A verdict with confirmed, refuted, and unverified findings.

Jev exit codes:

| Exit | Meaning | Workflow action |
|---|---|---|
| 0 | Pass | Continue; no automatic block |
| 2 | Send back | Fix the flagged axes, or record why the finding is not a defect |
| 3 | Unavailable, config, API, or secret-shaped input | Note "Jev unavailable" and use the independent review path |
| 4 | Requested model is gone | Stop; do not silently switch to a paid model |

A Jev send-back is advisory. It still needs a concrete fix or an explained
disagreement. A Jev pass does not replace the acceptance check.

## 7. Close

`/close <id>`:

- checks every acceptance item;
- runs the final review if there is a diff;
- runs Jev close triage when configured;
- appends one dated entry to the project's process ledger;
- records the evidence with `status <id> done --evidence "<command and result>"`;
- reports what passed, what remains unproven, and the next action.

A task stays active if evidence is missing.

## 8. Integrate

When lanes exist, `/integrate`:

- reads each task packet;
- refuses a task that is not `review` or `done`, has no evidence, or has a
  failing review;
- builds the merge order and checks for shared files;
- merges in order into one integration branch;
- stops on a conflict instead of guessing;
- runs the full project check on the merged tree;
- runs `/review` on the merged diff;
- updates each lane and creates an integration record.

A green lane is not a green integration. The merged tree gets the final check.

## Worked example

Task: add a `--dry-run` flag to a small command. The change touches one file and
one test. It is one reviewable diff, so it does not need a goal.

```sh
export HARNESS_HOME="$HOME/.config/opencode"
export HARNESS_STATE="$HOME/.local/state/libreharness"

ID=$(python3 "$HARNESS_HOME/bin/tasks.py" new "Add dry-run flag" \
  --project demo \
  --scope "Add --dry-run to the export command; no write when set." \
  --acceptance "- export --dry-run prints the plan and writes nothing
- existing export tests pass")

python3 "$HARNESS_HOME/bin/tasks.py" claim "$ID" --owner session-a
```

Implement, then run:

```sh
python3 -m unittest tests.test_export
```

Suppose the result is `12 tests, OK`. Review:

```text
/review <id>
```

If Jev is not configured, the command says "Jev unavailable" and uses the
independent review path. If the diff is low risk, `devils-advocate` is skipped.
Close:

```sh
python3 "$HARNESS_HOME/bin/tasks.py" status "$ID" done \
  --evidence "python3 -m unittest tests.test_export: 12 tests, OK"
```

The task's Evidence section now holds the command and result, and the metrics
file has one row. The board shows the task under Done.

## When not to use the queue

- A typo, a one-line copy fix, or a pure formatting change.
- A question that needs an answer, not a change.
- A read-only investigation that fits one turn and produces no diff.

Saying "this is trivial, no task" is a valid outcome. The queue is for work that
needs memory, ownership, review, or proof.

## Next

- [Command reference](command-reference.md)
- [Skills](skills.md)
- [Jev](jev.md)
