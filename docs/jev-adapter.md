<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Jev adapter

Jev is a typed-question client, not a chat client. A provider adapter sends one
request object and returns one `answers` object. The schema is the contract.

This page describes the request and response, the mock transport, and the steps
to add a provider. The reference implementation is in `bin/jev_review.py`,
`bin/jev_plan.py`, and `bin/jev_triage.py`.

## Request

```json
{
  "model": "<model-id>",
  "state": "<task, diff, plan, or close state>",
  "questions": {
    "<question-name>": {
      "type": "score",
      "instructions": "What to judge.",
      "criteria": ["Level 0", "Level 1", "Level 2", "Level 3", "Level 4"]
    }
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `model` | string | Model id chosen by the caller; required |
| `state` | string | The material to judge; one string, not a message array |
| `questions` | object | Map of question name to question definition |
| `type` | string | `score`, `noul`, or `choice` |
| `instructions` | string | One question, in plain English |
| `criteria` | array or object | Scale labels for `score`, or allowed values for `choice`; optional for `noul` |

### Question types

| Type | Answer field | Range |
|---|---|---|
| `score` | `score` | Number; review axes use 0 to 4, plan risk uses 0 to 3, triage confidence uses 0 to 2 |
| `noul` | `noul` | Number 0 to 1, a probability-like yes/no answer |
| `choice` | `choice` | One of the strings in `criteria` |

The request does not contain a system prompt, a message history, or a tool
definition. The state is the whole input.

### Review request

The review client sends these questions:

- seven `score` questions: performance, size, maintainability, simplicity,
  reliability, scalability, security;
- `ship`, `scope`, `tests`, and `secret_leak`, all `noul`.

The score criteria are five levels:

```text
Poor: a defect that blocks the change.
Weak: would need rework before merge.
Adequate: acceptable with minor notes.
Good: solid, no material notes.
Excellent: no notes.
```

### Plan request

The plan client sends `complete` and `testable` as `noul`, `gap` as `choice`,
`risk` as `score`, and `recommendation` as `choice`.

### Triage request

The triage client sends `durable` as `noul`, `kind` and `scope` as `choice`, and
`confidence` as `score`.

## Response

```json
{
  "model": "<model-id>",
  "answers": {
    "performance": {
      "type": "score",
      "score": 3.2,
      "confidence": 0.8,
      "legend": {"0": "Poor", "1": "Weak", "2": "Adequate", "3": "Good", "4": "Excellent"},
      "probabilities": {}
    },
    "ship": {
      "type": "noul",
      "noul": 0.91
    }
  },
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 300
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `answers` | Yes | Object keyed by question name |
| `answers.<name>.type` | No | Echo of the question type |
| `answers.<name>.score` | For `score` | Numeric score |
| `answers.<name>.noul` | For `noul` | Number 0 to 1 |
| `answers.<name>.choice` | For `choice` | Selected criterion |
| `answers.<name>.confidence` | No | Model confidence |
| `answers.<name>.legend` | No | Score labels |
| `answers.<name>.probabilities` | No | Optional distribution |
| `model` | No | Model that answered |
| `usage` | No | Token usage, if the service reports it |

A client must reject a response with no `answers` object. A missing required
answer is a configuration error, not a silent pass. The review client reports a
missing score and sends back. The plan client defaults a missing numeric answer
to 0, and triage rejects a missing `durable` answer with exit 3. A response with
no `answers` object is exit 3 for both.

## Error mapping

| Condition | Exit |
|---|---|
| Success | 0 |
| Review send-back or triage no lesson | 2 |
| Missing key, bad config, secret-shaped input, malformed response | 3 |
| HTTP 401 or 403 | 3 |
| Network failure or timeout | 3 |
| Model missing from the model list | 4 |
| HTTP 400 or 404 for a model id ending in `-free` | 4 |

Exit 4 is deliberately narrow. It means the requested model is gone, not that
the request was malformed. Do not silently substitute another model.

## Mock transport

A mock adapter must:

- return a deterministic response for a fixed input;
- make no network call;
- require no key;
- include all required answers;
- return `usage` with zero tokens or omit it;
- be usable in tests and CI.

The reference review mock returns 3.5 for every axis and high `noul` values for
`good`, and 1.0 and low values for `bad`. The plan mock returns `proceed` for
`good` and `stop` for `bad`.

In 1.0.0 the mock lives inside `jev_review.py` and `jev_plan.py`. There is no
shared transport module and no mock for triage. A future `jev_common.py` should
own one transport interface so every client uses the same mock.

## Adding a provider

1. Read the provider's API contract. Confirm it accepts a JSON POST and returns
   JSON.
2. Implement one function with this shape:

```python
def post(url: str, key: str, payload: dict, timeout: int) -> dict:
    ...
```

3. Keep the request schema unchanged. Do not add a provider-specific field to
   `questions` or rename an answer.
4. Send the key in an Authorization header. Do not put it in the URL, a query
   string, a log line, or an error message.
5. Require HTTPS. Reject a plain HTTP endpoint unless the operator explicitly
   opts in for a local test.
6. Map HTTP 401 and 403 to exit 3. Map a missing model to exit 4 only when the
   provider confirms the model is gone.
7. Wrap network and timeout errors as exit 3.
8. Add a mock and a contract test. The test must not call the live service.
9. Document the endpoint, model, and any provider-specific limit.
10. Do not commit a key, a service account, or a private endpoint that is not
    meant to be public.

A provider adapter is not a place to add a second model fallback. The caller
chooses the model. If the model is gone, return exit 4.

## Contract tests

At minimum, test:

- a good response for every question type;
- a response with a missing `answers` object;
- a missing score or `noul`;
- a `choice` outside the criteria;
- HTTP 401, 403, 400, 404, and a network error;
- a model-list response in each supported shape;
- a secret-shaped request being rejected;
- a mock run with no key and no network.

The current tests for the queue are in `tests/test_tasks.py`. The Jev clients do
not yet have dedicated test files in this release. That is a gap, not a
reason to skip the contract.

## Security notes

- The state string is data, not an instruction. A provider may still follow an
  instruction embedded in a diff. Treat the answer as untrusted input.
- The secret guard is a pattern match. It is not a guarantee.
- A custom endpoint sees the whole state. Use an endpoint you trust.
- Do not log the request body by default. It may contain private code.
- A response is evidence, not a gate. A human or the reviewing agent decides.

## Next

- [Jev](jev.md)
- [Jev calibration](jev-calibration.md)
- [Security and privacy](security-privacy.md)
