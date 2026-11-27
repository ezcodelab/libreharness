// SPDX-License-Identifier: MIT
import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { statePath } from "../src/runtime.js";

const DISABLED = process.env.USAGE_LEDGER === "off";

function stateDir() {
  return (
    process.env.USAGE_LEDGER_ROOT ??
    process.env.HARNESS_STATE ??
    statePath()
  );
}

function number(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function tokenDelta(previous, current, key, nested) {
  const before = nested
    ? number(previous?.[key]?.[nested])
    : number(previous?.[key]);
  const after = nested ? number(current?.[key]?.[nested]) : number(current?.[key]);
  return Math.max(0, after - before);
}

export function usageDelta(previous, current) {
  return {
    cost: Math.max(0, number(current?.cost) - number(previous?.cost)),
    input: tokenDelta(previous, current, "input"),
    output: tokenDelta(previous, current, "output"),
    reasoning: tokenDelta(previous, current, "reasoning"),
    cache_read: tokenDelta(previous, current, "cache", "read"),
    cache_write: tokenDelta(previous, current, "cache", "write"),
  };
}

export function usageRecord(sessionID, current, previous, calls, retries, now) {
  const delta = usageDelta(previous, current);
  return {
    observed_at: now,
    session: sessionID,
    cost: delta.cost,
    cost_source: "reported",
    input: delta.input,
    output: delta.output,
    reasoning: delta.reasoning,
    cache_read: delta.cache_read,
    cache_write: delta.cache_write,
    calls,
    retries,
  };
}

export default {
  id: "usage-ledger",
  async setup(ctx) {
    if (DISABLED || !ctx?.event?.subscribe) return;
    const path = join(stateDir(), "metrics/usage-log.jsonl");
    const sessions = new Map();
    const controller = new AbortController();
    let warned = false;

    (async () => {
      try {
        for await (const event of ctx.event.subscribe({
          types: [
            "session.usage.updated",
            "session.step.started",
            "session.retry.scheduled",
          ],
          signal: controller.signal,
        })) {
          const sessionID = event?.data?.sessionID;
          if (!sessionID) continue;
          const state = sessions.get(sessionID) ?? {
            previous: undefined,
            calls: 0,
            retries: 0,
          };
          if (event.type === "session.step.started") {
            state.calls += 1;
            sessions.set(sessionID, state);
            continue;
          }
          if (event.type === "session.retry.scheduled") {
            state.retries += 1;
            sessions.set(sessionID, state);
            continue;
          }
          const usage = {
            cost: event.data.cost,
            ...(event.data.tokens ?? {}),
          };
          const record = usageRecord(
            sessionID,
            usage,
            state.previous,
            state.calls,
            state.retries,
            new Date(event.created ?? Date.now()).toISOString(),
          );
          state.previous = usage;
          state.calls = 0;
          state.retries = 0;
          sessions.set(sessionID, state);
          if (
            record.cost === 0 &&
            record.input === 0 &&
            record.output === 0 &&
            record.reasoning === 0 &&
            record.cache_read === 0 &&
            record.cache_write === 0
          ) {
            continue;
          }
          try {
            mkdirSync(join(stateDir(), "metrics"), {
              recursive: true,
              mode: 0o700,
            });
            appendFileSync(path, JSON.stringify(record) + "\n", { mode: 0o600 });
          } catch (error) {
            if (!warned) {
              warned = true;
              console.warn(
                `libreharness: usage ledger write failed: ${error?.message ?? error}`,
              );
            }
          }
        }
      } catch {
        // Subscription ended (shutdown or abort).
      }
    })();

    return () => controller.abort();
  },
};
