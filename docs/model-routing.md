<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Model routing

The harness is provider-agnostic. It does not choose a provider or model for
you, and the core configuration contains no model ID. This page describes roles,
a static matrix, and the cost controls that matter.

## Roles, not brands

| Role | Capability needed | Cost policy | Harness surface |
|---|---|---|---|
| Explorer | Strong reading and search, large context, low risk | Cheapest model that can read the repository reliably | `explore` agent, `/brief`, `/takeover` |
| Planner | Strong reasoning, can decompose and spot gaps | Mid or high capability; plans are cheap compared with a wrong build | `/goal` plan mode, Jev plan critique |
| Implementer | Strong tool use and code editing, follows a bounded scope | Capable model; this is where a weak model costs the most | `implementer` agent |
| Reviewer | Strong reasoning, skeptical, can cite a source and a sink | Capable model; independent context matters more than speed | `/review`, `devils-advocate` agent |
| Integrator | Careful merge and test discipline, no guessing on conflicts | Capable model, narrower scope | `integrator` agent, `/close` integration step |
| Advisory Jev | Typed-question answering, structured output | Separate endpoint and model; advisory only | `bin/jev_*.py` |

A role is a requirement, not a product name. Any provider that supports the
needed tools and context can fill it.

## Core configuration

`opencode.example.json` has no `model` field. The agents in `agents/` do not set
a model. The commands do not set a model. The Jev client requires `JEV_MODEL`
for a live call and has no default.

That is deliberate. A hardcoded model goes stale, leaks a provider preference,
and makes a benchmark compare the model rather than the harness.

Choose a provider and model in OpenCode using its normal login and model picker,
or add a `model` field to `opencode.json`:

```json
{
  "model": "<provider>/<model-id>"
}
```

The exact value is provider-specific. Use the provider's own model list. Do not
copy a model ID from an example and assume it is current.

## Static matrix example

A cost-conscious release candidate can use one provider for every role. The
operator's current working matrix uses Ollama:

| Role | Model |
|---|---|
| build / default | `ollama-cloud/deepseek-v4.1-flash#max` |
| plan | `ollama-cloud/deepseek-v4-pro#high` |
| devils-advocate | `ollama-cloud/deepseek-v4-pro#high` |
| implementer | `ollama-cloud/deepseek-v4.1-flash#max` |
| integrator | `ollama-cloud/deepseek-v4.1-flash#max` |
| explore | `ollama-cloud/deepseek-v4.1-flash#max` |

This is an example, not a requirement. The public tree does not ship these IDs
as defaults.

## Cost controls

The harness gives you several:

| Control | Effect |
|---|---|
| WIP limit of 3 | Fewer parallel contexts and less repeated reading |
| `max_continuations` on a goal | Caps the continuation watcher |
| Agent step limits | `explore` 14, `devils-advocate` 24, `implementer` and `integrator` 32 |
| Jev `--max-chars` | Truncates the diff and task before egress; default 30000 |
| Jev `--timeout` | Stops a slow advisory call; default 90 seconds |
| Compaction settings | The example config compacts automatically and keeps 15000 tokens |
| Task scope | One reviewable diff, less context and fewer retries |

Step limits and compaction are not a cost guarantee. They are bounds you can
reason about.

## No automatic routing in 1.0.0

There is no free-model selector, retry model chain, or hidden provider switch in
the core. If a model is capped or unavailable, choose another model with
`/models` or wait. A future task covers a router with live availability,
capability, cost, and a visible fallback order.

Do not silently switch from a free model to a paid model. A silent paid call is
a billing surprise. Record the model actually used in the task evidence or
review note.

## Jev routing

Jev is separate from the OpenCode model. It uses:

- `JEV_ENDPOINT` for the typed-question call;
- `JEV_MODELS_URL` for the availability check;
- `JEV_MODEL` for the model id, required for a live call;
- `JEV_API_KEY` or `JEV_KEY_FILE` for the key.

The client does not choose a model, does not read a provider catalog for a
default, and does not switch models on its own. A 400 or 404 for a model id
ending in `-free` is reported as exit 4.

See [jev.md](jev.md) and [jev-adapter.md](jev-adapter.md).

## What is not supported

- A hosted routing service.
- Automatic model selection by benchmark score.
- A guarantee that a fallback preserves quality.
- A benchmark claim. None has been run.
