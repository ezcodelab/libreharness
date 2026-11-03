<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Jev

Jev is an advisory reviewer, planner, and close-triage client. It sends a
typed-question request to an HTTP endpoint and prints structured answers. For
when to use each client, see [When to use what](when-to-use.md).

Jev is not a gate. It does not merge, close, block, or approve anything by
itself. The operator or reviewing agent decides what to do with the answer.

Jev is optional. The queue, quickstart, commands, skills, plugins, and the full
test suite work without a key.

## The three clients

| Client | Use when | Input | What it asks |
|---|---|---|---|
| `bin/jev_review.py` | A diff needs a typed second opinion before close | A task and a diff | Seven quality axes, ship, scope, tests, secret leak |
| `bin/jev_plan.py` | A goal plan needs a completeness and risk check | A goal and its children | Complete, testable, largest gap, risk, recommendation |
| `bin/jev_triage.py` | Close is deciding whether a lesson is durable | A compact close state | Durable lesson, kind, scope, confidence |

All three print a human-readable result by default and JSON with `--json`.

## Configuration

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `JEV_ENDPOINT` | No | `https://opencode.ai/inference/systemone/v1/systemone` | Typed-question endpoint |
| `JEV_MODELS_URL` | No | `https://opencode.ai/inference/v1/models` | Model availability endpoint |
| `JEV_MODEL` | Yes for a live call | Unset | Model id; no hardcoded default |
| `JEV_API_KEY` | No | Unset | Key from the environment |
| `JEV_KEY_FILE` | No | Unset | Path to a key file; mode 600 |
| `JEV_MODE` | No | Unset | Contract values `live`, `mock`, `skip`; see implementation status |

`JEV_MODEL` is required for every live call. The client does not pick a model
from the catalog and does not hardcode a rotating free model. A model id that
appears in an example plugin is an example, not a Jev default.

The endpoint must be HTTPS. The reference client does not reject a plain HTTP
URL, so the choice is yours. A key is sent only to the configured endpoint.

## Key resolution

The client resolves a key in this order:

1. `--key-file <value>`: if the value is a file, read it; otherwise treat the
   value as the key.
2. `JEV_API_KEY`.
3. `OPENCODE_API_KEY`.
4. `TYPESAFE_API_KEY`.
5. `JEV_KEY_FILE` if the file exists and is non-empty.
6. `~/.config/opencode/jev.key` if it exists and is non-empty.

Use one source. Do not put the same key in several places.

The key file should be mode 600:

```sh
install -m 600 /dev/null "$HOME/.config/opencode/jev.key"
# Put the key in the file with your editor, then:
chmod 600 "$HOME/.config/opencode/jev.key"
```

Do not put the key in a shell history if you can avoid it. An environment
variable is visible to child processes of the session. A mode 600 file is the
better default on a shared machine.

## Setup

Export the model and the key source:

```sh
export JEV_MODEL="<model-id>"
export JEV_KEY_FILE="$HOME/.config/opencode/jev.key"
```

Or, for a short session:

```sh
export JEV_MODEL="<model-id>"
export JEV_API_KEY="<key>"
```

Check that the model is still offered:

```sh
python3 "$HARNESS_HOME/bin/jev_review.py" --check
```

`--check` calls the model list. It does not run a review. It exits 0 when the
model is present, 3 for a configuration or API error, and 4 when the model is
gone.

## No key

A missing key is a configuration error from a standalone client:

```text
error: no Jev key. Set OPENCODE_API_KEY, pass --key-file, or create
~/.config/opencode/console.key (chmod 600).
```

The exit code is 3. The message in rc.1 names `console.key`; the resolver reads
`jev.key`, `JEV_KEY_FILE`, and the environment variables above. Use those.

At the workflow level, a missing key is a skip:

- `/review` treats exit 3 as "Jev unavailable" and uses the independent review
  path.
- `/close` treats exit 3 as "Jev unavailable" and uses its own judgment.
- The quickstart and the test suite do not need a key.

The client does not exit 0 on a missing key. That would hide a misconfiguration
from a script. The slash commands are responsible for the skip decision.

## Exit codes

| Exit | Review | Plan | Triage |
|---|---|---|---|
| 0 | Pass | Result produced | Durable lesson |
| 2 | Send back | Not used | No durable lesson |
| 3 | Config, API, missing key, or secret-shaped input | Same | Same |
| 4 | Requested model is gone | Same | Same |

A review send-back is advisory. It still needs a concrete fix or an explained
disagreement. A triage "no durable lesson" is a valid result, not a failure.

## Review

```sh
python3 "$HARNESS_HOME/bin/jev_review.py" \
  --diff /tmp/opencode/review.diff \
  --task-file /tmp/opencode/review-task.txt
```

The review asks for seven axes on a five-level scale:

```text
performance, size, maintainability, simplicity, reliability, scalability, security
```

The score is 0 to 4. A score below 2.0 sends the change back. The other
questions are:

| Question | Type | Send-back threshold |
|---|---|---|
| `ship` | `noul` | below 0.5 |
| `scope` | `noul` | below 0.5 |
| `tests` | `noul` | below 0.5 |
| `secret_leak` | `noul` | above 0.5 |

`noul` is a number in 0 to 1 that answers a yes/no question. Higher means more
likely yes, except for `secret_leak`, where higher means more likely a leak.

The diff and task are truncated at `--max-chars`, default 30000. The client
refuses input that matches a secret-shaped pattern unless
`--allow-secret-shaped` is passed. That flag is for a reviewed exception, not a
convenience.

## Plan critique

```sh
python3 "$HARNESS_HOME/bin/jev_plan.py" --goal <goal-id>
```

The plan client reads the goal and its children from the queue. It asks:

| Question | Type | Meaning |
|---|---|---|
| `complete` | `noul` | Does the plan cover the goal and acceptance? |
| `testable` | `noul` | Does every child have an observable check? |
| `gap` | `choice` | `none`, `acceptance`, `dependency`, `risk`, `scope`, or `ambiguous` |
| `risk` | `score` | Low, Medium, High, Unacceptable |
| `recommendation` | `choice` | `proceed`, `revise`, or `stop` |

The client sets the recommendation to `revise` when `complete` or `testable`
is below 0.5, or when `gap` is not `none`, unless the service already said
`stop`. It forces `stop` when the risk score is 3 or higher.

The plan client does not edit the plan and does not block execution. It prints
a recommendation.

## Close triage

```sh
python3 "$HARNESS_HOME/bin/jev_triage.py" \
  --state /tmp/opencode/close-state-<id>.txt --json
```

The triage asks:

| Question | Type | Meaning |
|---|---|---|
| `durable` | `noul` | Is there a lesson that changes a future decision? |
| `kind` | `choice` | `none`, `task`, `process`, `design`, or `skill` |
| `scope` | `choice` | `project` or `global` |
| `confidence` | `score` | Low, Medium, High |

A result is durable when `durable` is at least 0.6 and `kind` is not `none`.
Triage is a suggestion. `/close` still writes at most one lesson and never
promotes a skill to global in that turn.

## Mock and dry run

`jev_review.py` and `jev_plan.py` support:

```sh
--dry-run   # print the request payload, no network
--mock good # canned pass
--mock bad  # canned send-back or stop
```

The mock still requires `JEV_MODEL`, because the client validates configuration
before the mock branch. It does not need a key.

`jev_triage.py` has no mock or dry-run in rc.1. If you need a no-network triage
test, test the parser with a fixture response in Python.

## JEV_MODE

The adapter contract defines `JEV_MODE` with three values:

| Value | Intended behavior |
|---|---|
| `live` | Call the configured endpoint; require a key and model |
| `mock` | Return a deterministic fixture; no network |
| `skip` | Print one line and exit successfully |

In 1.0.0-rc.1 the three clients do not read `JEV_MODE`. Use the command flags
and the exit-3 handling described above. Do not rely on `JEV_MODE` until the
changelog says it is implemented.

## Cost

Jev calls can be billed by the endpoint provider.

- The client does not estimate a dollar cost.
- The response may include a `usage` object, but the reference client does not
  print it in human output. The mock uses zero tokens.
- `--max-chars` bounds the request size, but not the response size.
- `--timeout` bounds latency, not spend.
- A `--check` call reads the model list and generally does not run inference.
- A retry is not automatic. A failed call is a failed call.

Record the model and endpoint with any review that relies on Jev, so a later
reader can tell what produced the answer.

## Privacy

Jev sends the following to the configured endpoint:

- the task statement and the diff, for review;
- the goal and child task text, for plan critique;
- the close state, for triage;
- the key in an Authorization header;
- the model id.

It does not send the queue, the board, the metrics file, the key file path, or
the rest of the repository unless that text is inside the task or diff you
pass.

The secret-shaped guard is a pattern match, not a data-loss prevention system.
It can miss a secret and it can flag a harmless string. Redact before you send.
Do not use `--allow-secret-shaped` on a diff you have not reviewed.

The client does not print the key. It does print service error bodies, which
may contain request details. Read an error before sharing it.

See [security-privacy.md](security-privacy.md) for the full boundary.

## Implementation status in 1.0.0-rc.1

| Area | Status |
|---|---|
| `JEV_MODEL` required, no hardcoded model | Implemented |
| `JEV_ENDPOINT`, `JEV_MODELS_URL` | Implemented |
| `JEV_API_KEY`, `JEV_KEY_FILE`, fallback key path | Implemented |
| `--check` model availability, exit 4 | Implemented |
| Review mock and dry run | Implemented |
| Plan mock and dry run | Implemented |
| Automatic plan critique from `/goal` | Not wired in rc.1; run `bin/jev_plan.py` directly |
| Triage mock and dry run | Not implemented |
| `JEV_MODE` | Documented contract, not read by the clients |
| Shared `bin/jev_common.py` | Not present; clients import shared functions from `jev_review.py` |
| Prompt templates in `jev/prompts/` | Not present; prompts are built in the clients |

The missing shared module and prompt files are a maintainability gap, not a
reason to trust the client more. Treat the adapter contract as the target and
the current code as the reference implementation.

## Next

- [Jev adapter](jev-adapter.md)
- [Jev calibration](jev-calibration.md)
- [Security and privacy](security-privacy.md)
