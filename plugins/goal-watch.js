// SPDX-License-Identifier: MIT
// goal-watch: continuation nudge for an active autorun goal. It never creates
// work or marks anything done; it only asks the session to continue. The goal
// carries its own continuation budget; no environment flag or relaunch.
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

export default {
  id: "goal-watch",
  async setup(ctx) {
    if (!ctx?.event?.subscribe || !ctx?.session?.prompt) return;
    const counts = new Map();
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
            goals = JSON.parse(await run(["goals", "--json"]));
          } catch {
            continue;
          }
          if (!Array.isArray(goals) || goals.length === 0) continue;
          if (goals.length > 1) continue; // run one autorun goal at a time
          const goal = goals[0];
          const id = goal.id;
          if (!id) continue;
          if (!goal.session || goal.session !== sessionID) continue;
          const max = maxContinuations(goal.max_continuations);
          const used = counts.get(id) ?? 0;
          if (used >= max) continue;
          let state;
          try {
            state = JSON.parse(await run(["goal-status", id, "--json"]));
          } catch {
            continue;
          }
          counts.set(id, used + 1);
          const next =
            state.ready?.length > 0
              ? `Next ready child: ${state.ready[0]}.`
              : state.closable
                ? "All children are final; run the final review and close the goal."
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
