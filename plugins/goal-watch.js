// SPDX-License-Identifier: MIT
// goal-watch: remind once per session when an active goal is closable, and
// continue one autorun goal while it has ready children. It never creates work,
// closes a goal, or marks anything done.
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const HOME =
  process.env.HARNESS_HOME ?? `${process.env.HOME}/.config/opencode`;
const ROOT =
  process.env.GOAL_WATCH_ROOT ??
  process.env.HARNESS_STATE ??
  `${process.env.HOME}/.local/state/libreharness`;
const TASKS = process.env.GOAL_WATCH_TASKS ?? `${HOME}/bin/tasks.py`;

export function maxContinuations(value) {
  if (value === undefined || value === null || value === "") return 12;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 12;
}

async function run(args) {
  const { stdout } = await execFileAsync("python3", [TASKS, ...args], {
    encoding: "utf8",
    timeout: 2500,
    // Do not hand the queue helper the provider/session environment.
    env: {
      PATH: process.env.PATH ?? "/usr/bin:/bin",
      HOME: process.env.HOME ?? "",
      HARNESS_STATE: ROOT,
      PYTHONDONTWRITEBYTECODE: "1",
    },
  });
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

export default {
  id: "goal-watch",
  async setup(ctx) {
    if (!ctx?.event?.subscribe || !ctx?.session?.prompt) return;
    const counts = new Map();
    const reminded = new Set();
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
          // It may belong to another session; the prompt says to ignore it if
          // this session is not working on that goal.
          let promptedClose = false;
          for (const goal of goals) {
            const id = goal?.id;
            const reminderKey = `${sessionID}:${id}`;
            if (!id || reminded.has(reminderKey)) continue;
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
          if (used >= max) continue;
          let state;
          try {
            state = JSON.parse(await run(["goal-status", id, "--json"]));
          } catch {
            continue;
          }
          if (state.closable) continue; // the close reminder owns this case
          counts.set(id, used + 1);
          const next =
            state.ready?.length > 0
              ? `Next ready child: ${state.ready[0]}.`
              : "No ready child; inspect the blocked/open children and stop if a person is needed.";
          try {
            await ctx.session.prompt({
              sessionID,
              text:
                `Continue the active goal ${id}. Run ` +
                `\`python3 ${TASKS} goal-status ${id} --json\`, then follow ` +
                `the goal skill. ${next} If this session is not working on ` +
                `${id}, ignore this message and do not start work. Do not repeat ` +
                `completed work; stop on a blocker, a one-way door, or an approval.`,
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
