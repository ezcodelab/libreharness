<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# FAQ

## What is this project?

A durable Markdown work queue, a risk-scaled engineering workflow, reusable
OpenCode agents, commands, skills, local plugins, and an advisory typed-question
reviewer called Jev.

## Is it a replacement for OpenCode?

No. It runs on top of OpenCode. OpenCode supplies the model, tools, sessions,
and agent runtime. The harness supplies workflow, state, review, and optional
advisory review.

## Do I need Jev?

No. Jev is optional. The queue, quickstart, commands, skills, plugins, and tests
work without a key.

## Do I need a model API key?

OpenCode needs a provider and a model. The harness does not choose either. A Jev
key is separate and optional.

## Which model should I use?

Your choice. The core has no model ID and the Jev client has no default. Pick a
model for each role based on capability, cost, context, and data terms. See
[model-routing.md](model-routing.md).

## Are the model IDs in the examples defaults?

No. They are examples of a routing pattern. They may rotate, disappear, or be
replaced. Do not copy one and assume it is current.

## Does Jev block a merge or a close?

No. Jev is advisory. A send-back still needs a concrete fix or an explained
disagreement. The operator or reviewing agent decides.

## What does Jev cost?

The endpoint provider decides. The client does not estimate a dollar cost and
does not print a usage summary in its human output. `--max-chars` and
`--timeout` bound the request size and latency. See [jev.md](jev.md).

## Is my code sent anywhere?

OpenCode sends prompts and context to the provider you choose. Jev sends the
task and diff, plan, or close state to the endpoint you configure. The queue
itself makes no network call. Read [security-privacy.md](security-privacy.md).

## Where is my data?

Tasks, board, metrics, lock, and an optional key file live under
`HARNESS_STATE`. Code and configuration live under `HARNESS_HOME`. Set both
explicitly. Do not put state inside the checkout.

## Does it work on Windows?

No, not in 1.0.0. The queue uses POSIX `fcntl`. The 1.1 preview is planned to
add a cross-platform lock layer. WSL2 may work but is not tested.

## Is it benchmarked?

No. The benchmark has not been run. This candidate makes no performance, cost,
or quality claim. A future claim needs a pre-registered protocol, fixed tasks,
raw data, an analysis script, and limitations.

## Why a Markdown queue instead of a database?

It is inspectable, diffable, portable, and needs no service. A task is a file
you can read, back up, or delete. The tradeoff is no query engine and no
built-in encryption. See [design-notes.md](design-notes.md).

## Can I use it with a private repository?

Yes, but check the data terms of your model provider and your Jev endpoint
first. A free model may have different terms from a paid model. The queue stores
plain Markdown, so use filesystem permissions and full disk encryption if the
state is sensitive.

## Can I use free models?

Yes, with caveats: data terms, rate limits, model drift, tool support, and
quality. Use them on public or low-sensitivity code unless you have checked the
terms. See [model-routing.md](model-routing.md).

## How do I add a command or skill?

A command is a Markdown file in `commands/` with frontmatter. A skill is
`skills/<name>/SKILL.md` with `name` and `description` frontmatter. Keep the
skill under 120 lines and evaluate it before promotion. See
[skills.md](skills.md).

## Why did my task not close?

The evidence gate rejected a placeholder or the task was never claimed. Use a
command and result, a measured check, or `[T]` with a plan. See
[troubleshooting.md](troubleshooting.md).

## What is the license?

MIT for code, commands, agents, skills, plugins, tests, and configuration. CC BY
4.0 for narrative documentation under `docs/`. Code snippets in docs are MIT.
See [LICENSE](../LICENSE) and [docs/LICENSE](LICENSE).

## Is there support?

Best effort, no SLA, no bounty. Security reports follow
[SECURITY.md](../SECURITY.md). Third-party plugins, custom providers, custom Jev
adapters, Windows, and private knowledge integrations are outside 1.0.0
support.

## Can I contribute?

Yes. Read [CONTRIBUTING.md](../CONTRIBUTING.md). One task, one reviewable diff.
Sign off with `git commit -s`. No secrets.

## What is planned after 1.0.0?

A Windows 1.1 preview with a cross-platform lock layer, and a narrow multi-agent
1.2 preview. Neither is a 1.0.0 deliverable. See
[design-notes.md](design-notes.md).

## Does the harness preserve chat history?

No. Chat history is the host's concern. The harness preserves task state,
evidence, handoffs, and lessons. That is deliberate: a task should survive a
session without carrying the whole transcript.
