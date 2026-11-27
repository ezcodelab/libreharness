// SPDX-License-Identifier: MIT
// goal-watch: remind once per session when an active goal is closable, and
// continue one autorun goal while it has ready children. It never creates work,
// closes a goal, or marks anything done.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { resolvePython, statePath } from "../src/runtime.js";

const execFileAsync = promisify(execFile);

const HOME =
  process.env.HARNESS_HOME ?? `${process.env.HOME}/.config/opencode`;
const ROOT =
  process.env.GOAL_WATCH_ROOT ??
  process.env.HARNESS_STATE ??
  statePath();
const TASKS = process.env.GOAL_WATCH_TASKS ?? `${HOME}/bin/tasks.py`;

export function maxContinuations(value) {
  if (value === undefined || value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

export function progressSignature(state) {
  return JSON.stringify({
    counts: state?.counts ?? {},
    ready: state?.ready ?? [],
    open: state?.open ?? [],
  });
}

export function continuationAllowed({ max, used, previous, state }) {
  if (max !== null) return used < max;
  return previous !== progressSignature(state);
}

export function continuationChild(state) {
  return Array.isArray(state?.ready) && state.ready.length > 0
    ? state.ready[0]
    : "";
}

async function run(args) {
  const env = {
    PATH: process.env.PATH ?? "/usr/bin:/bin",
    HOME: process.env.HOME ?? "",
    HARNESS_STATE: ROOT,
    PYTHONDONTWRITEBYTECODE: "1",
  };
  const python = resolvePython({ env });
  const { stdout } = await execFileAsync(
    python.command,
    [...python.prefixArgs, TASKS, ...args],
    {
      encoding: "utf8",
      timeout: 2500,
      env,
    },
  );
  return stdout.trim();
}

function closeReminder(goal) {
  const title = goal.title ? ` (${goal.title})` : "";
  return (
    `Reminder: goal ${goal.id}${title} is ready to close; all children are final. ` +
    `Do not close it automatically. Ask the operator to reply "close now" to ` +
    `run /close ${goal.id}, or "later" to keep it open. If this session is not ` +
    `working on ${goal.id}, ignore this reminder.`
  );
}

function stopReminder(goal, reason, state) {
  const counts = state?.counts ?? {};
  const summary = Object.entries(counts)
    .filter(([, value]) => value > 0)
    .map(([status, value]) => `${status}=${value}`)
    .join(" ");
  const ready = Array.isArray(state?.ready) && state.ready.length > 0
    ? state.ready.join(", ")
    : "none";
  const open = Array.isArray(state?.open) && state.open.length > 0
    ? state.open.join(", ")
    : "none";
  return (
    `Stopped goal ${goal.id}: ${reason}. Current state: ${summary || "empty"}; ` +
    `ready: ${ready}; open: ${open}. Do not start another implementation pass. ` +
    `Record the best current evidence, the blocker, and one bounded next action ` +
    `in the task Handoff with State, Decisions, Files, Checks, Open, Next, and ` +
    `Context, then stop.`
  );
}

export default {
  id: "goal-watch",
  async setup(ctx) {
    if (!ctx?.event?.subscribe || !ctx?.session?.prompt) return;
    const counts = new Map();
    const reminded = new Set();
    const stopped = new Set();
    const seen = new Map();
    const controller = new AbortController();

    (async () => {
      try {
        for await (const event of ctx.event.subscribe({
          types: ["session.idle"],
          signal: controller.signal,
        })) {
          const sessionID = event?.data?.sessionID;
          if (!sessionID) continue;
          let goals;
          try {
            goals = JSON.parse(await run(["goals", "--all", "--json"]));
          } catch {
            continue;
          }
          if (!Array.isArray(goals) || goals.length === 0) continue;

          // A closable goal is more important than a continuation nudge.
          let promptedClose = false;
          for (const goal of goals) {
            const id = goal?.id;
            const reminderKey = `${sessionID}:${id}`;
            if (!id || goal?.session !== sessionID || reminded.has(reminderKey)) continue;
            let state;
            try {
              state = JSON.parse(await run(["goal-status", id, "--json"]));
            } catch {
              continue;
            }
            if (!state.closable) continue;
            reminded.add(reminderKey);
            try {
              await ctx.session.prompt({ sessionID, text: closeReminder(goal) });
            } catch {
              // The session may be closing; a missed reminder is safe.
            }
            promptedClose = true;
            break;
          }
          if (promptedClose) continue;

          const active = goals.filter(
            (goal) =>
              goal?.session === sessionID &&
              (goal.autorun === true || goal.autorun === "true"),
          );
          if (active.length !== 1) continue; // run one autorun goal at a time
          const goal = active[0];
          const id = goal.id;
          if (!id) continue;
          const max = maxContinuations(goal.max_continuations);
          const used = counts.get(id) ?? 0;
          let state;
          try {
            state = JSON.parse(await run(["goal-status", id, "--json"]));
          } catch {
            continue;
          }
          if (state.closable) continue; // the close reminder owns this case
          const next = continuationChild(state);
          let reason = "";
          if (max !== null && used >= max) {
            reason = "continuation budget exhausted";
          } else if (
            !continuationAllowed({ max, used, previous: seen.get(id), state })
          ) {
            reason = "no progress since the previous continuation";
          } else if (!next) {
            reason = "no ready child to continue";
          }
          if (reason) {
            const key = [
              sessionID,
              id,
              reason,
              progressSignature(state),
            ].join(":");
            if (!stopped.has(key)) {
              stopped.add(key);
              try {
                await ctx.session.prompt({
                  sessionID,
                  text: stopReminder(goal, reason, state),
                });
              } catch {
                // The session may be closing; a missed stop notice is safe.
              }
            }
            continue;
          }
          seen.set(id, progressSignature(state));
          counts.set(id, used + 1);
          try {
            await ctx.session.prompt({
              sessionID,
              text:
                `Continue the active goal ${id}. Run ` +
                `\`python3 ${TASKS} goal-status ${id} --json\`, then follow ` +
                `the goal skill. Next ready child: ${next}. ` +
                `Do not repeat completed work; stop on a blocker, a one-way door, ` +
                `or an approval.`,
            });
          } catch {
            // The session may be closing; a missed nudge is safe.
          }
        }
      } catch {
        // Subscription ended (shutdown or abort).
      }
    })();

    return () => controller.abort();
  },
};
