// SPDX-License-Identifier: MIT
// auto-intake: turn a nontrivial prompt into an inbox task before the model
// answers. It never blocks admission on failure and never stores a prompt that
// looks like it contains a secret. Opt out with AUTO_INTAKE=off.
import { execFileSync } from "node:child_process";
import { appendFileSync, mkdirSync, readFileSync, readdirSync } from "node:fs";
import { basename, join } from "node:path";
import { minimalEnv, resolvePython, statePath } from "../src/runtime.js";

function homeDir() {
  return process.env.HARNESS_HOME ?? `${process.env.HOME}/.config/opencode`;
}

function stateDir() {
  return (
    process.env.AUTO_INTAKE_ROOT ??
    process.env.HARNESS_STATE ??
    statePath()
  );
}

function tasksCli() {
  return process.env.AUTO_INTAKE_TASKS ?? `${homeDir()}/bin/tasks.py`;
}

const DISABLED = process.env.AUTO_INTAKE === "off";

const ACTION =
  /\b(fix|add|implement|build|refactor|investigate|debug|review|design|migrate|test|document|deploy|update|remove|rename|optimi[sz]e|audit|release|create|write|change|make|repair|verify)\b/i;
const QUESTION_ONLY =
  /^\s*(how|what|why|when|where|who|is|are|do|does|did)\b/i;
const CONTINUE =
  /^\s*(continue|go on|keep going|yes|ok|okay|proceed|retry|again|done)\b/i;
const DELEGATION =
  /^\s*(you are|act as|role:|read-only|independent|focused|re-?review|implement one explicitly|task may be complete)/i;

export const PLAYBOOK_IDS = [
  "investigation",
  "bug-fix",
  "feature",
  "refactoring",
  "perf",
  "hillclimb",
  "autonomous-multiphase",
  "correct",
];

export const BLOCKED_NOTICE =
  "[workflow] BLOCKED: engineering-loop is missing or invalid; no task was created";
const HELPER_FAILURE_NOTICE =
  "[workflow] Queue helper unavailable; no task was created. Load engineering-loop and run its playbook router before editing.";

function frontmatterName(text) {
  if (!text.startsWith("---\n")) return null;
  const end = text.indexOf("\n---", 4);
  if (end < 0) return null;
  for (const line of text.slice(4, end).split(/\r?\n/)) {
    const match = line.match(/^name:\s*(.+)$/);
    if (match) return match[1].trim().replace(/^["']|["']$/g, "");
  }
  return null;
}

export function validateWorkflow(home) {
  const errors = [];
  const skillPath = join(home, "skills/engineering-loop/SKILL.md");
  const referenceDir = join(
    home,
    "skills/engineering-loop/references/playbooks",
  );
  let skill = "";
  try {
    skill = readFileSync(skillPath, "utf8");
  } catch {
    errors.push(`missing ${skillPath}`);
  }
  if (skill) {
    const name = frontmatterName(skill);
    if (name !== "engineering-loop") {
      errors.push(
        `skill name ${name ?? "missing"} must be engineering-loop in ${skillPath}`,
      );
    }
  }
  const playbooks = new Set();
  try {
    for (const name of readdirSync(referenceDir)) {
      if (name.endsWith(".md")) playbooks.add(name.slice(0, -3));
    }
  } catch {
    errors.push(`missing ${referenceDir}`);
  }
  for (const id of PLAYBOOK_IDS) {
    if (!playbooks.has(id)) errors.push(`missing playbook ${id}`);
  }
  return { ok: errors.length === 0, errors, playbooks };
}

const NAMED_PLAYBOOK = /\b(?:the\s+)?([a-z][a-z-]+)\s+playbook\b/i;
const MULTI_STEP =
  /\b(multi-step|multi-phase|multiphase|multi-deliverable|unattended|autorun|going to bed|run until done|until done|overnight)\b/i;
const HILLCLIMB =
  /\b(hillclimb|hill-climb|throughput|lines\/sec|target metric|commit only (?:measured )?wins)\b/i;
const PERF =
  /\b(slow|slower|latency|latencies|profile|profiling|p9\d|speed (?:it|this) up|takes? \d+(?:\.\d+)?\s*(?:ms|s|seconds?|milliseconds?))\b/i;
const REFACTOR =
  /\b(refactor|refactoring|simplify|extract|split|move|rename|inline|consolidate)\b/i;
const DEFECT =
  /\b(bug|bugs|broken|break|breaks|breaking|fails?|failing|failure|error|errors|crash(?:es|ed|ing)?|regression|wrong|incorrect|fix|fixes|fixing|repair)\b/i;
const EDIT =
  /\b(add|adds|build|change|changes|commit|consolidate|correct|create|debug|delete|drop|extract|fix|hillclimb|implement|improve|increase|inline|make|migrate|move|optimi[sz]e|profile|reduce|refactor|remove|rename|repair|replace|rewrite|simplify|speed|split|update|wire|write)\b/i;
const LEAD_READ_ONLY =
  /^\s*(investigate|explain|trace|describe|analy[sz]e|review|audit|find out|how|what|why|when|where|who|is|are|do|does|did)\b/i;

export function routePrompt(text) {
  const input = String(text ?? "");
  const named = input.match(NAMED_PLAYBOOK);
  const namedId = named && PLAYBOOK_IDS.includes(named[1].toLowerCase())
    ? named[1].toLowerCase()
    : null;
  const multiStep = MULTI_STEP.test(input);

  const defect = DEFECT.test(input) && EDIT.test(input);
  const readOnly = LEAD_READ_ONLY.test(input) && !EDIT.test(input);

  let playbook;
  if (namedId) {
    playbook = namedId;
  } else if (multiStep) {
    playbook = "autonomous-multiphase";
  } else if (defect) {
    playbook = "bug-fix";
  } else if (readOnly) {
    playbook = "investigation";
  } else if (HILLCLIMB.test(input)) {
    playbook = "hillclimb";
  } else if (PERF.test(input)) {
    playbook = "perf";
  } else if (REFACTOR.test(input)) {
    playbook = "refactoring";
  } else if (EDIT.test(input)) {
    playbook = "feature";
  } else {
    playbook = "investigation";
  }

  if (playbook === "autonomous-multiphase") {
    return {
      playbook,
      userNamed: namedId !== null,
      multiStep: true,
      skills: ["engineering-loop", "goal"],
    };
  }
  return {
    playbook,
    userNamed: namedId !== null,
    multiStep,
    skills: multiStep ? ["engineering-loop", "goal"] : ["engineering-loop"],
  };
}

function routeLine(decision) {
  return decision.skills.includes("goal")
    ? "Route through engineering-loop with the goal skill for this multi-step run"
    : "Route through engineering-loop";
}

function queueNotice(id, decision) {
  return (
    `[queue] Task ${id} was created for this request. ${routeLine(decision)} ` +
    `(playbook: ${decision.playbook}; read only ` +
    `skills/engineering-loop/references/playbooks/${decision.playbook}.md). ` +
    `For one reviewable diff, write concrete ` +
    `acceptance plus the Data shape and Verify lines, claim it, then work in ` +
    `this turn. Use the work-queue brief only for a multi-deliverable or ambiguous request. ` +
    `Implement, verify, review, close, and ship. Honor a playbook the user ` +
    `named. Stop only at the contract's human gates. Do not ask the operator ` +
    `to retype a command.`
  );
}

function reusedNotice(id, decision) {
  return (
    `[queue] Existing task ${id} matches this request. Use it; do not create ` +
    `a duplicate. ${routeLine(decision)} (playbook: ${decision.playbook}; read ` +
    `only skills/engineering-loop/references/playbooks/${decision.playbook}.md). ` +
    `For one reviewable diff, complete the acceptance, Data shape, and Verify ` +
    `lines, claim it, then work in this turn; use the work-queue brief only when scope is ` +
    `still ambiguous. Then implement, verify, review, close, and ship.`
  );
}

// This list must stay at least as strict as the review client's secret patterns.
const SECRET =
  /(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk[_-](live|test)?[_-]?[A-Za-z0-9]{10,}|xox[baprs]-[A-Za-z0-9-]{10,}|Bearer\s+eyJ[A-Za-z0-9._-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|password|token|access[_-]?key)\s*[:=]\s*(?:"[^"]{8,}"|'[^']{8,}'|\S{8,}))/i;
const PII =
  /([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https?:\/\/\S+|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b)/gi;

const seen = new Map();
let ledgerWarned = false;

function sanitize(text) {
  return text.replace(SECRET, "[redacted]").replace(PII, "[redacted]");
}

function nontrivial(text) {
  if (!text || text.length < 12) return false;
  if (text.startsWith("/") || text.startsWith("@")) return false;
  if (DELEGATION.test(text) || CONTINUE.test(text)) return false;
  if (QUESTION_ONLY.test(text)) return false;
  return ACTION.test(text) || text.length > 160;
}

function titleOf(text) {
  return sanitize(text.split("\n")[0]).trim().slice(0, 72);
}

function slugOf(text) {
  return titleOf(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

function existingTask(text) {
  const suffix = `-${slugOf(text)}`;
  try {
    const file = readdirSync(`${stateDir()}/work/tasks`).find(
      (name) => name.endsWith(".md") && name.includes(suffix),
    );
    if (!file) return null;
    const body = readFileSync(`${stateDir()}/work/tasks/${file}`, "utf8");
    return /^status:\s*(inbox|ready)\s*$/m.test(body) ? file.slice(0, -3) : null;
  } catch {
    return null;
  }
}

function recordSessionTask(sessionID, taskID) {
  try {
    mkdirSync(`${stateDir()}/metrics`, { recursive: true, mode: 0o700 });
    appendFileSync(
      `${stateDir()}/metrics/session-tasks.jsonl`,
      JSON.stringify({
        observed_at: new Date().toISOString(),
        session: sessionID,
        task: taskID,
      }) + "\n",
      { mode: 0o600 },
    );
  } catch (error) {
    if (!ledgerWarned) {
      ledgerWarned = true;
      console.warn(
        `libreharness: session-task ledger write failed: ${error?.message ?? error}`,
      );
    }
  }
}

function createTask(text, directory, sessionID) {
  const title = titleOf(text);
  const project = basename(directory || "") || "general";
  const env = minimalEnv({
    HARNESS_STATE: stateDir(),
    PYTHONDONTWRITEBYTECODE: "1",
  });
  const python = resolvePython({ env });
  const output = execFileSync(
    python.command,
    [
      ...python.prefixArgs,
      tasksCli(),
      "new",
      "--project",
      project,
      "--status",
      "inbox",
      "--session",
      sessionID,
      "--scope",
      "Auto-captured prompt; confirm scope and acceptance, then add Data shape and Verify lines before claiming.",
      "--acceptance",
      "- [ ] TBD: confirm before claiming.",
      "--",
      title,
    ],
    {
      encoding: "utf8",
      timeout: 2500,
      stdio: ["ignore", "pipe", "pipe"],
      env,
    },
  );
  return output.trim().split("\n").pop();
}

export default {
  id: "auto-intake",
  async setup(ctx) {
    if (DISABLED || !ctx?.session?.hook) return;
    const workflow = validateWorkflow(homeDir());
    await ctx.session.hook("prompt", (event) => {
      const text = event?.prompt?.text ?? "";
      const sessionID = event?.sessionID ?? event?.session?.id ?? "unknown";
      if (text.startsWith("/close")) {
        seen.delete(sessionID);
        return;
      }
      if (!nontrivial(text) || SECRET.test(text)) return;
      if (seen.has(sessionID)) return;
      if (!workflow.ok) {
        seen.set(sessionID, "blocked");
        event.prompt.text = text + `\n\n${BLOCKED_NOTICE}`;
        return;
      }
      const decision = routePrompt(text);
      if (!workflow.playbooks.has(decision.playbook)) {
        seen.set(sessionID, "blocked");
        event.prompt.text = text + `\n\n${BLOCKED_NOTICE}`;
        return;
      }
      const existing = existingTask(text);
      if (existing) {
        seen.set(sessionID, existing);
        recordSessionTask(sessionID, existing);
        event.prompt.text = text + `\n\n${reusedNotice(existing, decision)}`;
        return;
      }
      try {
        const id = createTask(text, ctx.location?.directory, sessionID);
        seen.set(sessionID, id);
        recordSessionTask(sessionID, id);
        event.prompt.text = text + `\n\n${queueNotice(id, decision)}`;
      } catch {
        event.prompt.text = text + `\n\n${HELPER_FAILURE_NOTICE}`;
      }
    });
  },
};
