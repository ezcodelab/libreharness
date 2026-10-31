<!-- SPDX-License-Identifier: MIT -->
# Design: tenant-scoped audit export (clean fixture)

Status: reviewed draft. This is a synthetic benchmark fixture with no seeded
defects.

## Problem

Support engineers need a CSV export of one tenant's audit events for compliance
reviews. The admin UI shows one page at a time. Large tenants have millions of
events, so the export runs in the background and streams to object storage.

## Goals

- Let an authorized support engineer request an export for a tenant they can
  access.
- Stream the file without buffering it in memory.
- Make the download available for 24 hours.
- Keep every read and write scoped to one tenant.

## Non-goals

- Scheduled exports.
- Multi-tenant exports in one job.
- A general reporting system.

## API

Create a job with a client-generated idempotency key:

```http
POST /exports
Idempotency-Key: 8f14e45f-ea2b-4c3d-9e4f-1a2b3c4d5e6f
Content-Type: application/json

{"tenant_id": "ten_123"}
```

The gateway authenticates the caller and checks that the caller has the
`support_export` role **and** an entitlement to `ten_123`. The tenant id is
validated against the caller's entitlements on create, poll, and download.

The response is `202 Accepted` with a job id. A repeated request with the same
idempotency key returns the existing job instead of creating another.

Poll with:

```http
GET /exports/{job_id}
```

The response contains `status`, `created_at`, `completed_at`, an error message
when failed, and a signed download URL when complete. The signed URL expires
after 24 hours.

## Worker

The API writes the job row and publishes the job id in the same database
transaction using an outbox table. A relay publishes outbox rows to the
`exports` queue and marks them sent. The worker claims one job with a lease that
it renews while it runs.

The worker reads audit events in keyset-paged batches ordered by
`(created_at, id)`, bounded by the job's `created_at` snapshot. It writes CSV
rows to a per-job temporary object, flushes and closes the object, then moves it
to the final key. A failed attempt leaves the temporary object for the cleanup
job and records a terminal `failed` status with an error.

Object keys are `exports/<tenant_id>/<job_id>.csv`. A job never overwrites
another job's object. The temporary key includes the job id and attempt number.

## Data model

The migration is additive and reversible:

1. add `tenant_id uuid` as nullable;
2. backfill from the existing job owner with a bounded batch job;
3. add the `NOT NULL` constraint after the backfill;
4. add an index on `(tenant_id, created_at)`.

The down migration drops the index, the constraint, and the column. The rollout
runs the backfill before the constraint and records the batch progress.

There is a partial unique index on `(tenant_id)` for active jobs, so a second
active job for a tenant returns `409 Conflict`. The idempotency key is unique
per caller and tenant.

## Failure handling

- A worker crash is recovered by lease expiry; a redelivery starts a new
  attempt with a new temporary key.
- A terminal failure records `failed` and the error; the tenant can request a
  new job.
- A job that exceeds the 30-minute execution limit fails and releases the
  partial unique index.
- The cleanup job deletes temporary objects older than one hour and final
  objects after the 24-hour download window.

## Security

- The worker opens a tenant-scoped database session and sets the tenant context
  before reading audit events. RLS is enabled and forced on the audit table.
- The signed URL is scoped to one object and expires after 24 hours.
- CSV fields are quoted with RFC 4180 rules, and values beginning with `=`,
  `+`, `-`, or `@` are prefixed with a single quote to prevent formula
  injection.
- Logs never contain the CSV body, signed URL, or tenant data.

## Tests

- Create, poll, and download a one-row export.
- Empty tenant returns a header-only file.
- A 10,000-event export crosses multiple pages and contains every event once.
- A worker crash after the temporary write is retried and produces one final
  file.
- A repeated create with the same idempotency key returns one job.
- A caller without tenant entitlement gets `403` on create, poll, and download.
- The migration runs on a populated table and rolls back.
- A field containing a comma, quote, newline, and formula prefix is escaped.

## Open questions

None. The retention window and URL lifetime are fixed at 24 hours.
