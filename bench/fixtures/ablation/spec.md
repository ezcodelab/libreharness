<!-- SPDX-License-Identifier: MIT -->
# Design: tenant-scoped CSV export

Status: draft for review. This is a synthetic benchmark fixture, not a real
product design.

## Problem

Support teams need a CSV export of a tenant's audit events for compliance
reviews. The current admin UI can show one page at a time, but it cannot
produce a complete file. Large tenants have millions of events, so the export
must run in the background and must not block the request path.

## Goals

- Let an authorized support engineer request an export for one tenant.
- Stream the result to object storage instead of buffering it in memory.
- Let the engineer download the finished file for 24 hours.
- Keep the work isolated per tenant.

## Non-goals

- A general reporting system.
- Scheduled or recurring exports.
- Exporting data from more than one tenant in a single job.

## Proposed design

### API

The client creates a job:

```http
GET /exports?tenant_id=...
```

The response is `202 Accepted` with a job id:

```json
{"job_id": "ex_123", "status": "queued"}
```

The client polls for completion:

```http
POST /exports/ex_123
```

The response is the job status and, when ready, a signed download URL.

### Worker

The API writes a row to `export_jobs` and publishes a job id to the `exports`
queue. A worker claims one job at a time, reads audit events in keyset-paged
batches, writes CSV rows to a temporary object, and moves the object to the
final key when the last page is written. The worker deletes the temporary
object on failure.

### Authorization

The gateway checks that the caller has the `support_export` role. Tenant scope
is enforced by the gateway, and RLS handles the rest. The worker trusts the
tenant id stored on the job row.

### Data model

The migration adds a tenant column to `export_jobs`:

```sql
ALTER TABLE export_jobs
  ADD COLUMN tenant_id uuid NOT NULL;
```

The job row also stores `requested_by`, `status`, `object_key`, `created_at`,
and `completed_at`.

### Failure handling

If the worker crashes, the queue redelivers the job after the visibility
timeout. The worker is idempotent at the object level: it overwrites the same
temporary key and moves it once. The API returns `409 Conflict` if a second
request arrives for the same tenant while a job is running.

### Tests

- An authorized user can create a job and poll it to completion.
- An unauthorized user gets `403`.
- A tenant cannot see another tenant's job.
- The worker writes the expected header and one row for a fixture with 1,000
  events.

## Open questions

- Should the signed URL be valid for 24 hours or 1 hour?
- Do we need a separate retention job for orphaned objects?
