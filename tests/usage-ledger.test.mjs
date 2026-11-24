// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = mkdtempSync(join(tmpdir(), "usage-ledger-"));
process.env.USAGE_LEDGER_ROOT = root;
const { default: plugin, usageDelta, usageRecord } = await import(
  new URL(`../plugins/usage-ledger.js?test=${process.pid}`, import.meta.url)
);

assert.deepEqual(
  usageDelta(
    {
      cost: 0.1,
      input: 100,
      output: 20,
      reasoning: 5,
      cache: { read: 40, write: 10 },
    },
    {
      cost: 0.25,
      input: 160,
      output: 30,
      reasoning: 8,
      cache: { read: 70, write: 12 },
    },
  ),
  {
    cost: 0.15,
    input: 60,
    output: 10,
    reasoning: 3,
    cache_read: 30,
    cache_write: 2,
  },
);
const first = usageRecord(
  "ses_one",
  { cost: 0.2, input: 10, output: 2, reasoning: 1, cache: { read: 3, write: 1 } },
  undefined,
  4,
  1,
  "2026-11-23T12:00:00.000Z",
);
assert.equal(first.cost, 0.2);
assert.equal(first.calls, 4);
assert.equal(first.retries, 1);
assert.equal(first.cost_source, "reported");

const seen = [];
const queue = [];
let waiter;
const emit = (event) => {
  if (waiter) {
    const resolve = waiter;
    waiter = undefined;
    resolve(event);
  } else {
    queue.push(event);
  }
};
const ctx = {
  event: {
    subscribe: ({ types }) => {
      seen.push(...types);
      return (async function* () {
        while (true) {
          const event = queue.length
            ? queue.shift()
            : await new Promise((resolve) => {
                waiter = resolve;
              });
          yield event;
        }
      })();
    },
  },
};
const cleanup = await plugin.setup(ctx);
emit({
  type: "session.step.started",
  created: Date.parse("2026-11-23T12:00:00.000Z"),
  data: { sessionID: "s1" },
});
emit({
  type: "session.retry.scheduled",
  created: Date.parse("2026-11-23T12:00:01.000Z"),
  data: { sessionID: "s1" },
});
emit({
  type: "session.usage.updated",
  created: Date.parse("2026-11-23T12:00:02.000Z"),
  data: {
    sessionID: "s1",
    cost: 0.5,
    tokens: {
      input: 100,
      output: 20,
      reasoning: 5,
      cache: { read: 60, write: 8 },
    },
  },
});
await new Promise((resolve) => setTimeout(resolve, 30));
cleanup();
const path = join(root, "metrics/usage-log.jsonl");
assert.ok(existsSync(path), "usage log was not written");
const log = readFileSync(path, "utf8").trim().split("\n").map(JSON.parse);
assert.equal(log.length, 1);
assert.equal(log[0].session, "s1");
assert.equal(log[0].cost, 0.5);
assert.equal(log[0].input, 100);
assert.equal(log[0].cache_read, 60);
assert.equal(log[0].calls, 1);
assert.equal(log[0].retries, 1);
assert.deepEqual(seen.sort(), [
  "session.retry.scheduled",
  "session.step.started",
  "session.usage.updated",
]);
assert.ok(!JSON.stringify(log).includes("prompt"), "ledger contains prompt data");
rmSync(root, { recursive: true, force: true });
console.log("usage-ledger: PASS");
