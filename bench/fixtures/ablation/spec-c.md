<!-- SPDX-License-Identifier: MIT -->
# Design: customer webhook delivery

Status: draft for review. This is a synthetic benchmark fixture, not a real
product design.

## Problem

Customers want to receive events such as `invoice.paid` and `user.created` at
their own HTTPS endpoint. The current system sends a fire-and-forget POST from
the request path. A slow endpoint blocks the request, and failed deliveries are
lost. The new design adds a queue and retries.

## Goals

- Deliver each event to the customer's configured endpoint.
- Retry transient failures without blocking the request path.
- Let the customer see recent delivery attempts.
- Preserve event ordering per customer.

## Non-goals

- A general event bus.
- Customer-defined transformations.
- More than one endpoint per customer.

## Proposed design

### Event creation

When an event is committed, the API writes a row to `webhook_outbox` in the same
transaction and returns. A relay reads unsent rows and publishes them to the
`webhooks` queue. The queue message contains the event id, customer id, and
endpoint URL.

### Delivery

The worker POSTs the event payload to the endpoint. It includes the customer id
in an `X-Customer-Id` header and the event id in `X-Event-Id`. The customer
verifies the request by comparing `X-Customer-Id` with its own id.

On a non-2xx response or a timeout, the worker retries with exponential backoff.
There is no maximum attempt count; the queue keeps redelivering until the
endpoint returns 2xx.

### Payload

The payload is the event JSON. The worker logs the full request body and the
response body at `info` level so support can debug failures.

### Ordering

The worker processes one message at a time per customer by using a queue
partition key of `customer_id`.

### Data model

`webhook_outbox` has `event_id`, `customer_id`, `payload`, `created_at`, and
`sent_at`. `webhook_attempts` has `event_id`, `attempt`, `status_code`,
`error`, and `created_at`.

### Tests

- A 2xx response marks the outbox row sent.
- A 500 response schedules a retry.
- The attempt row records the status code.
- Two events for one customer are delivered in order.

## Open questions

- Should the retry backoff start at one second or five seconds?
- Do we need a customer-facing replay button?
