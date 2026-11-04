<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Security and privacy

This page describes the trust boundary of the harness. It does not describe the
security of OpenCode, your provider, your operating system, or a third-party
plugin. Those are separate.

## The boundary

```text
your machine
  |
  |-- HARNESS_HOME: code, commands, skills, plugins, config
  |
  |-- HARNESS_STATE: tasks, board, metrics, lock, optional key file
  |
  |-- OpenCode process
        |
        |-- provider API: prompts, context, tool output
        |
        |-- Jev endpoint: task text and diff, plan text, or close state
        |
        |-- optional MCP servers and external plugins
```

The harness itself has no telemetry, no analytics, and no network call from the
queue. The egress comes from the tools you configure.

## What is stored locally

| Path | Content | Sensitivity |
|---|---|---|
| `$HARNESS_STATE/work/tasks/*.md` | Task title, scope, acceptance, context, plan, evidence, handoff, log | May contain project names, code snippets, and personal notes |
| `$HARNESS_STATE/work/BOARD.md` | Generated summary of tasks | Same as tasks, but shorter |
| `$HARNESS_STATE/work/.lock` | Empty lock file | None |
| `$HARNESS_STATE/metrics/workflow-log.csv` | Task id, project, dates, and up to 160 characters of evidence | May contain a command or result |
| `$HARNESS_STATE/jev.key` or your key path | Jev API key, if you choose a file | Secret |
| `$HARNESS_HOME/opencode.json` | Provider and model choice, permissions, optional MCP and plugin list | May contain a private endpoint or account detail |

The queue does not encrypt task files. It relies on filesystem permissions and,
if you need it, full disk encryption. State should be mode 700 and key files
mode 600. The queue uses the process umask, so set `umask 077` if your default
is permissive.

Task files are plain Markdown. They are easy to inspect, diff, back up, and
delete. They are also easy to copy by accident. Do not put a secret in a task,
a handoff, a lesson, or a log.

## What is sent to a model provider

OpenCode sends what the model needs to answer: the prompt, the conversation
context, file contents the agent reads, tool output, and the model configuration.
That is true with or without this harness.

The harness adds no hidden provider call. It does add workflow text: task
packets, briefs, skill bodies, command text, and review instructions. Those
become part of the prompt. If a task contains a customer name or a private URL,
the provider may see it.

Review your provider's data retention and training terms before using a
provider on sensitive code. A free model may have different terms from a paid
model. See [model-routing.md](model-routing.md).

## What is sent to Jev

Jev is the only harness component that sends code to a second service. It sends:

| Client | Data |
|---|---|
| Review | Task statement and diff, truncated at 30000 characters by default |
| Plan | Goal and child task text, truncated at 12000 characters |
| Triage | Close state, truncated at 12000 characters |

It also sends the model id and the key in an Authorization header. It does not
send the queue, board, metrics, key file path, or the rest of the repository
unless that text is in the state you pass.

The secret-shaped guard checks for common token prefixes, private key headers,
and `api_key`, `secret`, `password`, or `token` assignments. It is a pattern
match. It can miss a secret and it can flag harmless text. Redact before you
send. `--allow-secret-shaped` bypasses the guard; use it only after a review.

The endpoint must be HTTPS. The reference client does not enforce that, so check
your configuration. A custom endpoint sees the whole state. Use one you trust.

Jev is advisory. Do not send it a diff you would not send to a code reviewer
under the same confidentiality terms.

## What the plugins do

| Plugin | Local work | Network |
|---|---|---|
| `auto-intake` | Runs `tasks.py new` with a sanitized title; refuses secret-shaped prompts | None |
| `close-reminder` | Tracks tool activity and calls `notify-send` on Linux | None |
| `goal-watch` | Reads the queue and prompts the session | None |
| `security-guard` | Pattern-scans edit input after the tool runs | None |

The example config also includes a remote `grep-app` MCP server. If you keep it,
OpenCode may send search queries to `https://mcp.grep.app`. Remove the entry if
you do not want that egress. External plugins and MCP servers are not covered by
this policy.

## Secret handling

- Never commit a key, token, password, private key, `.env` file, auth store, or
  session export.
- Prefer `JEV_KEY_FILE` with mode 600, or a short-lived `JEV_API_KEY` in the
  environment. Use one source.
- Do not put a key on a command line. It can appear in process listings and
  shell history.
- Do not paste a key into a prompt, task, review, or issue. The model provider
  and Jev endpoint would see it.
- Rotate a key immediately if it appears in a diff, log, session export, or
  public issue. Removing the line does not undo the exposure.
- The Jev client does not print the key. It does print service error bodies.
  Read an error before sharing it.
- `auto-intake` refuses to create a task from a prompt that matches its secret
  patterns. The prompt still goes to the model provider as usual. That is a
  queue-storage guard, not a guarantee. A secret can be split, encoded, or
  shaped in a way the pattern misses.

## No secrets in state

The state directory is for work, not credentials. The one exception is a key
file that a client explicitly reads, such as `JEV_KEY_FILE`. Keep it mode 600
and outside task files.

If you back up state, treat the backup as sensitive. If you share a task,
redact it first. If you publish a fixture, use synthetic data.

## What is not protected

- A provider's logging, retention, training, or breach.
- A malicious repository or prompt injection that convinces an agent to run a
  command or read a file it should not.
- A third-party plugin, MCP server, or custom Jev adapter.
- A shell command that reaches the network.
- A leaked key that was already committed. Rotate it.
- A state directory on a shared machine with permissive permissions.
- macOS and Windows in 1.0.0; Linux is the only supported platform.

## Reporting

Follow [SECURITY.md](../SECURITY.md). Do not open a public issue with exploit
details, a key, a private path, or personal data.

## Next

- [Jev](jev.md)
- [Install](install.md)
- [Troubleshooting](troubleshooting.md)
