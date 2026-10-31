// SPDX-License-Identifier: MIT
// close-reminder: after real tool work has been quiet for a while, notify or
// (opt-in) prompt once per session. Default is a desktop notification: zero
// model tokens. It never writes a lesson; /close does the judgment. ESM.
import { execFile } from "node:child_process";

const NUDGE =
  "Task may be complete. Run /close when you are done: final /review if " +
  "needed, Jev triage, one project lesson (or `none`), and an optional " +
  "skill candidate. Do not promote to global; /tune does that.";

const MUTATING = new Set(["write", "edit", "patch", "apply_patch", "bash", "shell"]);
const IDLE_MS = Number(process.env.CLOSE_REMINDER_MS ?? 1800000); // 30 minutes
const MODE = process.env.CLOSE_REMINDER_MODE ?? "notify"; // notify | prompt | off

function desktopNotify(text) {
  if (process.platform !== "linux") return;
  try {
    execFile("notify-send", ["OpenCode", text], { timeout: 3000 }, () => {});
  } catch {
    // No notify-send or no desktop session: the next session still reminds.
  }
}

export default {
  id: "close-reminder",
  async setup(ctx) {
    if (MODE === "off") return;
    if (!ctx?.event?.subscribe || !ctx.tool?.hook) return;
    if (MODE === "prompt" && !ctx?.session?.prompt) return;

    const state = new Map(); // sessionID -> { count, mutating }
    const nudged = new Set();
    const timers = new Map();
    const controller = new AbortController();

    const clear = (sessionID) => {
      const timer = timers.get(sessionID);
      if (timer) {
        clearTimeout(timer);
        timers.delete(sessionID);
      }
    };

    const schedule = (sessionID) => {
      if (nudged.has(sessionID) || timers.has(sessionID)) return;
      const work = state.get(sessionID);
      if (!work) return;
      if (!work.mutating && work.count < 3) return;
      const timer = setTimeout(async () => {
        timers.delete(sessionID);
        if (nudged.has(sessionID)) return;
        nudged.add(sessionID);
        if (MODE === "prompt") {
          try {
            await ctx.session.prompt({ sessionID, text: NUDGE });
          } catch {
            // The session may be closing; a missed prompt is safe.
          }
        } else {
          desktopNotify(NUDGE);
        }
      }, IDLE_MS);
      timers.set(sessionID, timer);
    };

    try {
      await ctx.tool.hook("execute.before", (event) => {
        const sessionID = event?.sessionID;
        if (!sessionID) return;
        clear(sessionID);
        const current = state.get(sessionID) ?? { count: 0, mutating: false };
        current.count += 1;
        if (MUTATING.has(event.tool)) current.mutating = true;
        state.set(sessionID, current);
      });
    } catch {
      return;
    }

    (async () => {
      try {
        for await (const event of ctx.event.subscribe({
          types: ["session.idle", "session.execution.started"],
          signal: controller.signal,
        })) {
          const sessionID = event?.data?.sessionID;
          if (!sessionID) continue;
          if (event.type === "session.execution.started") {
            clear(sessionID);
          } else if (event.type === "session.idle") {
            schedule(sessionID);
          }
        }
      } catch {
        // Subscription ended (shutdown or abort).
      }
    })();

    return () => {
      controller.abort();
      for (const timer of timers.values()) clearTimeout(timer);
      timers.clear();
    };
  },
};
