<!-- SPDX-License-Identifier: MIT -->
# Design: self-service API key rotation

Status: draft for review. This is a synthetic benchmark fixture, not a real
product design.

## Problem

Customers need to rotate an API key without opening a support ticket. The
current flow requires an operator to generate a new key in the admin console,
send it to the customer, and revoke the old key by hand. The new flow should let
an authenticated customer rotate a key from the dashboard and see the new key
once.

## Goals

- Let a customer rotate a key for their own account.
- Show the new key exactly once, at creation.
- Keep existing integrations working through the change.
- Record who rotated which key and when.

## Non-goals

- Rotating keys for another tenant.
- Rotating more than one key in a single request.
- Importing keys from another provider.

## Proposed design

### API

The dashboard calls:

```http
GET /keys/{key_id}/rotate
```

The response is `200 OK` with the new key in a query parameter so the dashboard
can copy it:

```json
{"new_key": "sk_live_...", "key_id": "key_123"}
```

The gateway checks that the caller is authenticated and has the `customer`
role. The endpoint loads the key by `key_id` and rotates it.

### Rotation flow

1. Generate a new key with the same scopes as the old key.
2. Write the new key hash to `api_keys`.
3. Mark the old key `revoked_at = now()`.
4. Return the new plaintext key to the caller.
5. Write an audit event with the actor and key id.

The old key is revoked immediately. The dashboard tells the customer to update
their integration after the response.

### Data model

`api_keys` already has `id`, `account_id`, `key_hash`, `scopes`, `created_at`,
and `revoked_at`. The rotation adds no columns. The new key is stored as a hash,
and the plaintext is returned once.

### Failure handling

If step 2 succeeds and step 3 fails, the old key stays active. The operator can
revoke it manually. If the response is lost after step 4, the customer can
rotate again; the first new key remains valid until it is revoked.

### Tests

- An authenticated customer can rotate a key and receives a new key.
- The old key no longer works after rotation.
- The audit event contains the actor and key id.
- A request for a key that does not exist returns `404`.

## Open questions

- Should the dashboard show the new key in a modal or copy it to the clipboard?
- Do we need a separate notification email?
