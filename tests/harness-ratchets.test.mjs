// SPDX-License-Identifier: MIT
// Structural ratchets for the harness's own instructions. Each check is a pure
// function of a root directory so the self-tests at the bottom exercise the same
// code the repository scan runs.
import assert from "node:assert/strict";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export const MAX_SKILL_LINES = 120;
export const MAX_AGENTS_LINES = 110;
export const MAX_ENFORCEMENT_ROWS = 4;
export const MAX_PLAYBOOK_LINES = 25;
export const MIN_PLAYBOOK_STEPS = 3;
export const MAX_PLAYBOOKS_FILE_LINES = 180;

export const ASCII_IGNORE_GLOBS = [
  "CHANGELOG.md",
  "docs/process-lessons.md",
  "src/generated/**",
  "plugins/generated/**",
  ".opencode/node_modules/**",
];

export const COMMENT_IGNORE_GLOBS = [
  "node_modules/**",
  ".git/**",
  "tests/**",
  "src/generated/**",
  "plugins/generated/**",
];

const ASCII_SCOPE_FILES = [
  "AGENTS.md",
  "README.md",
  "CONTRIBUTING.md",
  "docs/reference.md",
];
const ASCII_SCOPE_DIRS = ["skills", ".opencode", "commands", "agents", "src", "plugins"];
const ASCII_EXTENSIONS = new Set([".md", ".js", ".mjs", ".py"]);

const FORBIDDEN_CHARACTERS = [
  ["\u2014", "em dash (U+2014)"],
  ["\u2013", "en dash (U+2013)"],
  ["\u2018", "curly single quote (U+2018)"],
  ["\u2019", "curly single quote (U+2019)"],
  ["\u201c", "curly double quote (U+201C)"],
  ["\u201d", "curly double quote (U+201D)"],
];

const FORBIDDEN_COMMENTS = [
  [/\bwork[-\s]?around\b/i, "workaround justification"],
  [/\bdo not (remove|delete|change|edit|modify|rename)\b/i, "do-not-change constraint"],
  [/\b(TODO|FIXME|XXX)\b/, "unresolved marker"],
];
const COMMENT_ALLOW = /comment-discipline:\s*allow\s+\S/i;
const COMMENT_REFERENCE = /(https?:\/\/|#\d+|\bCVE-\d{4}-\d{1,}|\bRFC\s?\d+)/i;

const PLAYBOOKS = [
  "investigation",
  "bug-fix",
  "feature",
  "refactoring",
  "perf",
  "hillclimb",
  "autonomous-multiphase",
  "correct",
];

function rel(root, path) {
  return relative(root, path).split("\\").join("/");
}

function countLines(text) {
  const lines = text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  return lines.length;
}

function frontmatter(text) {
  if (!text.startsWith("---\n")) return null;
  const end = text.indexOf("\n---", 4);
  if (end < 0) return null;
  const meta = {};
  for (const line of text.slice(4, end).split("\n")) {
    const match = line.match(/^([\w-]+):\s*(.*)$/);
    if (match && match[1] !== "") meta[match[1]] = match[2].trim();
  }
  return meta;
}

function ignored(relPath, globs) {
  return globs.some((glob) => {
    if (glob.endsWith("/**")) return relPath === glob.slice(0, -3) || relPath.startsWith(glob.slice(0, -2));
    return relPath === glob;
  });
}

function walk(dir, files = []) {
  if (!existsSync(dir)) return files;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path, files);
    else if (entry.isFile()) files.push(path);
  }
  return files;
}

function section(text, heading) {
  const padded = `\n${text}`;
  const start = padded.indexOf(`\n${heading}\n`);
  if (start < 0) return null;
  const rest = padded.slice(start + heading.length + 2);
  const next = rest.search(/\n## /);
  return next < 0 ? rest : rest.slice(0, next);
}

function hasHeading(path, heading) {
  if (!existsSync(path)) return false;
  const padded = `\n${readFileSync(path, "utf8")}`;
  return padded.includes(`\n${heading}\n`) || padded.includes(`\n${heading}\r\n`);
}

function has(file, needle) {
  return existsSync(file) && readFileSync(file, "utf8").includes(needle);
}

function push(problems, rule, file, message, line) {
  problems.push(line ? { rule, file, line, message } : { rule, file, message });
}

export function formatProblem(problem) {
  const location = problem.line ? `${problem.file}:${problem.line}` : problem.file;
  return `${problem.rule}: ${location}: ${problem.message}`;
}

export function checkSkillBudgets(root) {
  const problems = [];
  for (const base of [join(root, "skills"), join(root, ".opencode", "skills")]) {
    if (!existsSync(base)) continue;
    for (const entry of readdirSync(base, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = join(base, entry.name);
      const file = join(directory, "SKILL.md");
      const relDir = rel(root, directory);
      if (!existsSync(file)) {
        push(problems, "skill-budget", relDir, "missing SKILL.md");
        continue;
      }
      const relFile = rel(root, file);
      const text = readFileSync(file, "utf8");
      const lines = countLines(text);
      if (lines > MAX_SKILL_LINES) {
        push(
          problems,
          "skill-budget",
          relFile,
          `${lines} lines exceeds ${MAX_SKILL_LINES}; move detail into references/ and keep the entry short`,
        );
      }
      const meta = frontmatter(text);
      if (!meta) {
        push(problems, "skill-budget", relFile, "missing YAML frontmatter");
        continue;
      }
      if (!meta.name) push(problems, "skill-budget", relFile, "frontmatter needs a name");
      else if (meta.name !== entry.name) {
        push(problems, "skill-budget", relFile, `frontmatter name "${meta.name}" must match the directory "${entry.name}"`);
      }
      if (!meta.description) push(problems, "skill-budget", relFile, "frontmatter needs a description");
    }
  }
  return problems;
}

export function checkAsciiProse(root) {
  const problems = [];
  const files = [];
  for (const name of ASCII_SCOPE_FILES) {
    const path = join(root, name);
    if (existsSync(path)) files.push(path);
  }
  for (const name of ASCII_SCOPE_DIRS) {
    for (const path of walk(join(root, name))) {
      if (ASCII_EXTENSIONS.has(path.slice(path.lastIndexOf(".")))) files.push(path);
    }
  }
  for (const path of files) {
    const relPath = rel(root, path);
    if (ignored(relPath, ASCII_IGNORE_GLOBS)) continue;
    const lines = readFileSync(path, "utf8").split("\n");
    lines.forEach((line, index) => {
      for (const [character, label] of FORBIDDEN_CHARACTERS) {
        if (!line.includes(character)) continue;
        push(problems, "ascii-prose", relPath, `replace ${label} with ASCII punctuation`, index + 1);
        break;
      }
    });
  }
  return problems;
}

export function checkCommentDiscipline(root) {
  const problems = [];
  for (const name of ["src", "plugins", "bin"]) {
    for (const path of walk(join(root, name))) {
      const extension = path.slice(path.lastIndexOf("."));
      if (![".js", ".mjs", ".py"].includes(extension)) continue;
      const relPath = rel(root, path);
      if (ignored(relPath, COMMENT_IGNORE_GLOBS)) continue;
      const lines = readFileSync(path, "utf8").split("\n");
      lines.forEach((line, index) => {
        const trimmed = line.trim();
        const isComment = extension === ".py" ? trimmed.startsWith("#") : trimmed.startsWith("//");
        if (!isComment || trimmed.startsWith("#!") || /SPDX-License-Identifier/.test(trimmed)) return;
        if (COMMENT_ALLOW.test(line) || COMMENT_REFERENCE.test(line)) return;
        for (const [pattern, label] of FORBIDDEN_COMMENTS) {
          if (!pattern.test(trimmed)) continue;
          push(
            problems,
            "comment-discipline",
            relPath,
            `${label}; encode the constraint in a type, lint, or test, or add an external reference. See skills/no-comments/SKILL.md`,
            index + 1,
          );
          break;
        }
      });
    }
  }
  return problems;
}

export function checkAgentsBudget(root) {
  const problems = [];
  const file = join(root, "AGENTS.md");
  if (!existsSync(file)) return [{ rule: "agents-budget", file: "AGENTS.md", message: "missing AGENTS.md" }];
  const text = readFileSync(file, "utf8");
  const lines = countLines(text);
  if (lines > MAX_AGENTS_LINES) {
    push(problems, "agents-budget", "AGENTS.md", `${lines} lines exceeds ${MAX_AGENTS_LINES}; move procedure into skills/`);
  }
  if (hasHeading(file, "## Task scale")) {
    push(problems, "agents-budget", "AGENTS.md", "routing belongs in skills/engineering-loop, not always-on AGENTS.md");
  }
  for (const heading of ["## Commands", "## Boundaries", "## Rule enforcement"]) {
    if (!hasHeading(file, heading)) push(problems, "agents-budget", "AGENTS.md", `missing ${heading}`);
  }
  const enforcement = section(text, "## Rule enforcement");
  if (enforcement !== null) {
    const rows = enforcement
      .split("\n")
      .filter((line) => line.trim().startsWith("|"))
      .filter((line) => !/^\|[\s|:-]+\|$/.test(line.trim()))
      .slice(1);
    if (rows.length > MAX_ENFORCEMENT_ROWS) {
      push(
        problems,
        "agents-budget",
        "AGENTS.md",
        `Rule enforcement has ${rows.length} rows; keep at most ${MAX_ENFORCEMENT_ROWS} suite rows and append per-rule detail to skills/correct/references/rule-ledger.md`,
      );
    }
  }
  return problems;
}

export function checkRelativeLinks(root) {
  const problems = [];
  const scope = [
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "docs/reference.md",
    ...walk(join(root, "skills")).map((path) => rel(root, path)),
    ...walk(join(root, "commands")).map((path) => rel(root, path)),
    ...walk(join(root, "agents")).map((path) => rel(root, path)),
    ...walk(join(root, ".opencode", "skills")).map((path) => rel(root, path)),
  ].filter((name) => name.endsWith(".md"));
  for (const name of scope) {
    const path = join(root, name);
    if (!existsSync(path)) continue;
    readFileSync(path, "utf8")
      .split("\n")
      .forEach((line, index) => {
        for (const match of line.matchAll(/!?\[[^\]]*\]\(([^)\s]+)\)/g)) {
          const target = match[1];
          if (/^[a-z][a-z0-9+.-]*:/i.test(target) || target.startsWith("#")) continue;
          const clean = decodeURI(target.split("#")[0].split("?")[0]);
          if (!clean) continue;
          if (!existsSync(resolve(dirname(path), clean))) {
            push(problems, "relative-link", name, `link target does not exist: ${target}`, index + 1);
          }
        }
      });
  }
  return problems;
}

export function checkRouterWiring(root) {
  const problems = [];
  const router = join(root, "skills/engineering-loop/SKILL.md");
  const playbooks = join(root, "skills/engineering-loop/references/playbooks.md");

  for (const heading of ["## Playbook router", "## Fallback"]) {
    if (!hasHeading(router, heading)) push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", `missing ${heading}`);
  }
  if (!has(router, "references/playbooks.md")) {
    push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", "must link references/playbooks.md");
  }
  if (!existsSync(playbooks)) {
    push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", "missing playbook reference");
  } else {
    const text = readFileSync(playbooks, "utf8");
    if (countLines(text) > MAX_PLAYBOOKS_FILE_LINES) {
      push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", `${countLines(text)} lines exceeds ${MAX_PLAYBOOKS_FILE_LINES}`);
    }
    for (const name of PLAYBOOKS) {
      const body = section(text, `## ${name}`);
      if (body === null) {
        push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", `missing playbook section ${name}`);
        continue;
      }
      const lines = body.split("\n").filter((line) => line.trim() !== "");
      const steps = lines.filter((line) => /^\s*(?:\d+\.|-)\s+\S/.test(line));
      if (lines.length > MAX_PLAYBOOK_LINES) {
        push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", `${name} has ${lines.length} lines, cap is ${MAX_PLAYBOOK_LINES}`);
      }
      if (steps.length < MIN_PLAYBOOK_STEPS) {
        push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", `${name} has ${steps.length} steps, needs at least ${MIN_PLAYBOOK_STEPS}`);
      }
    }
  }

  for (const [path, needles] of [
    [join(root, "commands/brief.md"), ["**Playbook**", "**Data shape**"]],
    [join(root, "agents/implementer.md"), ["Data shape", "no-comments"]],
  ]) {
    const name = rel(root, path);
    if (!existsSync(path)) {
      push(problems, "router-wiring", name, "missing file");
      continue;
    }
    const text = readFileSync(path, "utf8");
    for (const needle of needles) {
      if (!text.includes(needle)) push(problems, "router-wiring", name, `missing ${needle}`);
    }
  }
  return problems;
}

export function checkSkillWiring(root) {
  const problems = [];
  for (const [path, needles] of [
    [join(root, "skills/no-comments/SKILL.md"), ["## Keep exceptions", "MUST KILL"]],
    [join(root, "skills/correct/SKILL.md"), ["## Inverted pyramid", "references/rule-ledger.md"]],
    [join(root, "skills/unslop/SKILL.md"), ["## Prose rules"]],
  ]) {
    const name = rel(root, path);
    if (!existsSync(path)) {
      push(problems, "skill-wiring", name, "missing file");
      continue;
    }
    const text = readFileSync(path, "utf8");
    for (const needle of needles) {
      if (!text.includes(needle)) push(problems, "skill-wiring", name, `missing ${needle}`);
    }
  }
  const unslop = join(root, "skills/unslop/SKILL.md");
  if (hasHeading(unslop, "## Audit") || hasHeading(unslop, "## Fix")) {
    push(problems, "skill-wiring", "skills/unslop/SKILL.md", "prose-only skill must not carry a codebase audit mode");
  }
  for (const [path, forbidden] of [
    [join(root, "commands/review.md"), "P3 notes"],
    [join(root, "agents/devils-advocate.md"), "require a comment that says why"],
  ]) {
    if (has(path, forbidden)) {
      push(problems, "skill-wiring", rel(root, path), `remove "${forbidden}": comment workarounds are blocking findings`);
    }
  }
  return problems;
}

export function checkIntakeWiring(root) {
  const path = join(root, "plugins/auto-intake.js");
  if (!existsSync(path)) return [{ rule: "intake-wiring", file: "plugins/auto-intake.js", message: "missing file" }];
  if (!readFileSync(path, "utf8").includes("export function routePrompt")) {
    return [{ rule: "intake-wiring", file: "plugins/auto-intake.js", message: "missing export function routePrompt" }];
  }
  return [];
}

export function checkWorkflowWiring(root) {
  return [...checkRouterWiring(root), ...checkSkillWiring(root), ...checkIntakeWiring(root)];
}

// The scan grows with the refactor so every commit stays green. A check is added
// here in the same commit that makes it pass.
const CHECKS = [
  checkSkillBudgets,
  checkAsciiProse,
  checkCommentDiscipline,
  checkAgentsBudget,
  checkRelativeLinks,
  checkRouterWiring,
  checkSkillWiring,
  checkIntakeWiring,
];

function selfTests() {
  const tmp = mkdtempSync(join(tmpdir(), "harness-ratchets-"));
  try {
    mkdirSync(join(tmp, "skills/short"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/short/SKILL.md"),
      `---\nname: short\ndescription: valid\n---\n\n# Short\n`,
    );
    assert.deepEqual(checkSkillBudgets(tmp), [], "a valid short skill must pass");

    mkdirSync(join(tmp, "skills/long"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/long/SKILL.md"),
      `---\nname: long\ndescription: invalid\n---\n${"- step\n".repeat(MAX_SKILL_LINES)}`,
    );
    const longProblems = checkSkillBudgets(tmp);
    assert.ok(
      longProblems.some((problem) => problem.rule === "skill-budget" && problem.file === "skills/long/SKILL.md"),
      "a skill over the budget must fail",
    );

    mkdirSync(join(tmp, "skills/renamed"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/renamed/SKILL.md"),
      `---\nname: other\ndescription: mismatch\n---\n\n# Other\n`,
    );
    assert.ok(
      checkSkillBudgets(tmp).some((problem) => problem.message.includes("must match the directory")),
      "a mismatched frontmatter name must fail",
    );

    mkdirSync(join(tmp, "agents"), { recursive: true });
    writeFileSync(join(tmp, "agents/dash.md"), "# A\n\none \u2014 two\n");
    assert.ok(
      checkAsciiProse(tmp).some((problem) => problem.rule === "ascii-prose" && problem.file === "agents/dash.md"),
      "an em dash must fail",
    );
    writeFileSync(join(tmp, "agents/dash.md"), "# A\n\none - two\n");
    assert.deepEqual(checkAsciiProse(tmp), [], "ASCII punctuation must pass");

    writeFileSync(join(tmp, "CHANGELOG.md"), "artifact \u2014 allowed\n");
    assert.deepEqual(checkAsciiProse(tmp), [], "ignored history must pass");

    mkdirSync(join(tmp, "src"), { recursive: true });
    writeFileSync(join(tmp, "src/bad.js"), "// workaround: do not remove this\nconst x = 1;\n");
    assert.ok(
      checkCommentDiscipline(tmp).some((problem) => problem.rule === "comment-discipline" && problem.file === "src/bad.js"),
      "an unreferenced workaround comment must fail",
    );
    writeFileSync(join(tmp, "src/bad.js"), "// Workaround required by https://example.com/issue/1\nconst x = 1;\n");
    assert.deepEqual(checkCommentDiscipline(tmp), [], "an external reference must pass");
    writeFileSync(join(tmp, "src/bad.js"), "// comment-discipline: allow vendor quirk\n// TODO later\nconst x = 1;\n");
    assert.ok(
      checkCommentDiscipline(tmp).some((problem) => problem.line === 2),
      "an allow marker must be evaluated per line, not per file",
    );

    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n");
    assert.deepEqual(checkAgentsBudget(tmp), [], "a small enforced AGENTS.md must pass");
    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Task scale\n\nlong prose\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n");
    assert.ok(
      checkAgentsBudget(tmp).some((problem) => problem.message.includes("routing belongs in skills/engineering-loop")),
      "task-scale routing in AGENTS.md must fail",
    );

    mkdirSync(join(tmp, "commands"), { recursive: true });
    writeFileSync(join(tmp, "commands/ok.md"), "[ref](../AGENTS.md) and [ext](https://example.com) and [anchor](#top)\n");
    assert.deepEqual(checkRelativeLinks(tmp), [], "external and anchor links must be ignored");
    writeFileSync(join(tmp, "commands/ok.md"), "[gone](../missing.md)\n");
    assert.ok(
      checkRelativeLinks(tmp).some((problem) => problem.rule === "relative-link"),
      "a broken relative link must fail",
    );

    mkdirSync(join(tmp, "skills/engineering-loop/references"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/engineering-loop/SKILL.md"),
      "# Router\n\n## Playbook router\n\nSee references/playbooks.md.\n\n## Fallback\n\nUse feature.\n",
    );
    writeFileSync(
      join(tmp, "skills/engineering-loop/references/playbooks.md"),
      PLAYBOOKS.map((name) => `## ${name}\n\n1. one\n2. two\n3. three\n`).join("\n"),
    );
    mkdirSync(join(tmp, "skills/no-comments"), { recursive: true });
    writeFileSync(join(tmp, "skills/no-comments/SKILL.md"), "# No comments\n\n## Keep exceptions\n\nMUST KILL workarounds.\n");
    mkdirSync(join(tmp, "skills/correct"), { recursive: true });
    writeFileSync(join(tmp, "skills/correct/SKILL.md"), "# Correct\n\n## Inverted pyramid\n\nSee references/rule-ledger.md.\n");
    mkdirSync(join(tmp, "skills/unslop"), { recursive: true });
    writeFileSync(join(tmp, "skills/unslop/SKILL.md"), "# Unslop\n\n## Prose rules\n\nCut filler.\n");
    writeFileSync(join(tmp, "commands/brief.md"), "- **Playbook** x\n- **Data shape** y\n");
    writeFileSync(join(tmp, "agents/implementer.md"), "Name the Data shape, then run no-comments.\n");
    writeFileSync(join(tmp, "commands/review.md"), "review\n");
    writeFileSync(join(tmp, "agents/devils-advocate.md"), "review\n");
    mkdirSync(join(tmp, "plugins"), { recursive: true });
    writeFileSync(join(tmp, "plugins/auto-intake.js"), "export function routePrompt(text) { return text; }\n");
    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n");
    assert.deepEqual(checkWorkflowWiring(tmp), [], "complete wiring must pass");

    writeFileSync(join(tmp, "skills/engineering-loop/references/playbooks.md"), "## perf\n\n1. one\n");
    assert.ok(
      checkWorkflowWiring(tmp).some((problem) => problem.message.includes("needs at least")),
      "a hollow playbook section must fail",
    );

    writeFileSync(join(tmp, "commands/review.md"), "Report these as P3 notes.\n");
    assert.ok(
      checkWorkflowWiring(tmp).some((problem) => problem.message.includes("P3 notes")),
      "a non-blocking comment rule must fail",
    );
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

function main() {
  selfTests();
  const problems = CHECKS.flatMap((check) => check(ROOT));
  if (problems.length > 0) {
    for (const problem of problems) console.error(formatProblem(problem));
    console.error(`\nharness-ratchets: ${problems.length} problem(s)`);
    process.exit(1);
  }
  console.log(`harness-ratchets: PASS (${CHECKS.length} checks)`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
