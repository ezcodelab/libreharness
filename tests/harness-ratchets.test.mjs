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

export const MAX_ENFORCEMENT_ROWS = 4;
export const MIN_PLAYBOOK_STEPS = 3;

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

export function checkSkillStructure(root) {
  const problems = [];
  for (const base of [join(root, "skills"), join(root, ".opencode", "skills")]) {
    if (!existsSync(base)) continue;
    for (const entry of readdirSync(base, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = join(base, entry.name);
      const file = join(directory, "SKILL.md");
      const relDir = rel(root, directory);
      if (!existsSync(file)) {
        push(problems, "skill-structure", relDir, "missing SKILL.md");
        continue;
      }
      const relFile = rel(root, file);
      const text = readFileSync(file, "utf8");
      const meta = frontmatter(text);
      if (!meta) {
        push(problems, "skill-structure", relFile, "missing YAML frontmatter");
        continue;
      }
      if (!meta.name) push(problems, "skill-structure", relFile, "frontmatter needs a name");
      else if (meta.name !== entry.name) {
        push(problems, "skill-structure", relFile, `frontmatter name "${meta.name}" must match the directory "${entry.name}"`);
      }
      if (!meta.description) push(problems, "skill-structure", relFile, "frontmatter needs a description");
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

function balancedQuotes(prefix) {
  let quote = null;
  for (let index = 0; index < prefix.length; index += 1) {
    const character = prefix[index];
    if (quote) {
      if (character === "\\") index += 1;
      else if (character === quote) quote = null;
    } else if (character === '"' || character === "'" || character === "`") {
      quote = character;
    }
  }
  return quote === null;
}

function commentText(line, extension, state) {
  const chunks = [];
  let rest = line;

  if (state.block) {
    const end = rest.indexOf("*/");
    if (end < 0) return [rest];
    chunks.push(rest.slice(0, end));
    rest = rest.slice(end + 2);
    state.block = false;
  }

  if (extension !== ".py") {
    let start = rest.indexOf("/*");
    while (start >= 0 && balancedQuotes(rest.slice(0, start))) {
      const end = rest.indexOf("*/", start + 2);
      if (end < 0) {
        chunks.push(rest.slice(start));
        state.block = true;
        return chunks;
      }
      chunks.push(rest.slice(start, end + 2));
      rest = rest.slice(end + 2);
      start = rest.indexOf("/*");
    }
  }

  if (extension === ".py") {
    const index = rest.indexOf("#");
    if (index >= 0 && balancedQuotes(rest.slice(0, index))) chunks.push(rest.slice(index));
  } else {
    const index = rest.indexOf("//");
    if (index >= 0 && (index === 0 || /\s/.test(rest[index - 1])) && balancedQuotes(rest.slice(0, index))) {
      chunks.push(rest.slice(index));
    }
  }
  return chunks.length > 0 ? chunks : null;
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
      const state = { block: false };
      lines.forEach((line, index) => {
        const chunks = commentText(line, extension, state);
        if (chunks === null) return;
        if (COMMENT_ALLOW.test(line) || COMMENT_REFERENCE.test(line)) return;
        for (const chunk of chunks) {
          const trimmed = chunk.trim();
          if (trimmed.startsWith("#!") || /SPDX-License-Identifier/.test(trimmed)) continue;
          const hit = FORBIDDEN_COMMENTS.find(([pattern]) => pattern.test(trimmed));
          if (!hit) continue;
          push(
            problems,
            "comment-discipline",
            relPath,
            `${hit[1]}; encode the constraint in a type, lint, or test, or add an external reference. See skills/no-comments/SKILL.md`,
            index + 1,
          );
          break;
        }
      });
    }
  }
  return problems;
}

export function checkAgentsContract(root) {
  const problems = [];
  const file = join(root, "AGENTS.md");
  if (!existsSync(file)) return [{ rule: "agents-contract", file: "AGENTS.md", message: "missing AGENTS.md" }];
  const text = readFileSync(file, "utf8");
  if (hasHeading(file, "## Task scale")) {
    push(problems, "agents-contract", "AGENTS.md", "routing belongs in skills/engineering-loop, not always-on AGENTS.md");
  }
  for (const heading of ["## Commands", "## Boundaries", "## Rule enforcement"]) {
    if (!hasHeading(file, heading)) push(problems, "agents-contract", "AGENTS.md", `missing ${heading}`);
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
        "agents-contract",
        "AGENTS.md",
        `Rule enforcement has ${rows.length} rows; keep at most ${MAX_ENFORCEMENT_ROWS} suite rows and append per-rule detail to skills/correct/references/rule-ledger.md`,
      );
    }
  }
  return problems;
}

export function checkInstructionOwners(root) {
  const problems = [];
  const owner = "skills/README.md";
  const header = "| Skill | Use |";
  const ownerPath = join(root, owner);
  if (!existsSync(ownerPath)) {
    push(problems, "instruction-owners", owner, "missing the skill-map owner");
  } else if (!readFileSync(ownerPath, "utf8").includes(header)) {
    push(problems, "instruction-owners", owner, "the skill map must own the Skill | Use table");
  }
  for (const name of ["AGENTS.md", "README.md", "docs/reference.md"]) {
    const path = join(root, name);
    if (!existsSync(path)) {
      push(problems, "instruction-owners", name, "missing file");
      continue;
    }
    const text = readFileSync(path, "utf8");
    if (!/\]\([^)]*skills\/README\.md(?:#[^)]*)?\)/.test(text)) {
      push(problems, "instruction-owners", name, `must link to ${owner}`);
    }
  }
  const scope = [
    join(root, "AGENTS.md"),
    join(root, "README.md"),
    ...walk(join(root, "docs")),
    ...walk(join(root, "commands")),
    ...walk(join(root, "agents")),
    ...walk(join(root, "skills")),
    ...walk(join(root, ".opencode", "skills")),
  ].filter((path) => path.endsWith(".md"));
  for (const path of scope) {
    const relPath = rel(root, path);
    if (relPath === owner) continue;
    if (ignored(relPath, ["CHANGELOG.md", "docs/process-lessons.md", "skills/correct/references/rule-ledger.md"])) continue;
    if (readFileSync(path, "utf8").includes(header)) {
      push(problems, "instruction-owners", relPath, `the skill map has one owner: ${owner}`);
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
  const index = join(root, "skills/engineering-loop/references/playbooks.md");
  const playbooks = join(root, "skills/engineering-loop/references/playbooks");

  for (const heading of ["## Playbook router", "## Fallback"]) {
    if (!hasHeading(router, heading)) push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", `missing ${heading}`);
  }
  if (!has(router, "references/playbooks/")) {
    push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", "must load references/playbooks/<id>.md");
  }
  for (const name of PLAYBOOKS) {
    if (!has(router, `\`${name}\``)) {
      push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", `router table is missing \`${name}\``);
    }
  }
  if (!existsSync(index)) {
    push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", "missing playbook index");
  } else {
    const text = readFileSync(index, "utf8");
    for (const name of PLAYBOOKS) {
      if (!text.includes(`playbooks/${name}.md`)) {
        push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", `index is missing ${name}`);
      }
    }
  }
  for (const name of PLAYBOOKS) {
    const file = `skills/engineering-loop/references/playbooks/${name}.md`;
    const path = join(root, file);
    if (!existsSync(path)) {
      push(problems, "router-wiring", file, "missing playbook file");
      continue;
    }
    const lines = readFileSync(path, "utf8").split("\n").filter((line) => line.trim() !== "");
    const steps = lines.filter((line) => /^\s*(?:\d+\.|-)\s+\S/.test(line));
    if (steps.length < MIN_PLAYBOOK_STEPS) {
      push(problems, "router-wiring", file, `${steps.length} steps, needs at least ${MIN_PLAYBOOK_STEPS}`);
    }
  }
  return problems;
}

const POLICY_TOKEN_PATTERNS = [
  [/jev_review/, "jev_review"],
  [/jev_plan/, "jev_plan"],
  [/jev_triage/, "jev_triage"],
  [/bin\/jev_/, "bin/jev_"],
  [/\bJev\b/, "Jev"],
  [/\bJEV_/, "JEV_"],
];
const POLICY_PHRASES = [
  "independent verifier PASS",
  "opposite-lens",
  "gate cannot certify",
];
const POLICY_IGNORE = [
  "CHANGELOG.md",
  "docs/process-lessons.md",
  "skills/correct/references/rule-ledger.md",
];

export function checkPolicyWiring(root) {
  const problems = [];
  const files = [];
  for (const base of ["commands", "agents", ".github/workflows"]) {
    for (const path of walk(join(root, base))) {
      const extension = path.slice(path.lastIndexOf("."));
      if ([".md", ".yml", ".yaml"].includes(extension)) files.push(path);
    }
  }
  for (const base of ["skills", ".opencode/skills"]) {
    for (const path of walk(join(root, base))) {
      if (path.endsWith("SKILL.md")) files.push(path);
    }
  }
  for (const name of ["README.md", "docs/reference.md", "SECURITY.md", "CONTRIBUTING.md"]) {
    const path = join(root, name);
    if (existsSync(path)) files.push(path);
  }
  for (const path of files) {
    const relPath = rel(root, path);
    if (ignored(relPath, POLICY_IGNORE)) continue;
    readFileSync(path, "utf8")
      .split("\n")
      .forEach((line, index) => {
        for (const [pattern, label] of POLICY_TOKEN_PATTERNS) {
          if (pattern.test(line)) {
            push(
              problems,
              "policy-wiring",
              relPath,
              `remove the agent-facing ${label} reference; the review artifact is the default gate`,
              index + 1,
            );
          }
        }
        for (const phrase of POLICY_PHRASES) {
          if (line.includes(phrase)) {
            push(
              problems,
              "policy-wiring",
              relPath,
              `remove "${phrase}"; policy is recorded in the review artifact`,
              index + 1,
            );
          }
        }
      });
  }
  return problems;
}

export function checkIntakeWiring(root) {
  const file = "plugins/auto-intake.js";
  const path = join(root, file);
  if (!existsSync(path)) return [{ rule: "intake-wiring", file, message: "missing file" }];
  const text = readFileSync(path, "utf8");
  const problems = [];
  if (!text.includes("export function routePrompt")) {
    push(problems, "intake-wiring", file, "missing export function routePrompt");
  }
  const list = text.match(/export const PLAYBOOK_IDS = \[([\s\S]*?)\];/);
  const ids = list ? [...list[1].matchAll(/"([^"]+)"/g)].map((match) => match[1]) : [];
  for (const id of PLAYBOOKS) {
    if (!ids.includes(id)) push(problems, "intake-wiring", file, `PLAYBOOK_IDS is missing ${id}`);
  }
  for (const id of ids) {
    if (!PLAYBOOKS.includes(id)) push(problems, "intake-wiring", file, `PLAYBOOK_IDS has unregistered id ${id}`);
  }
  return problems;
}

export function checkPrContract(root) {
  const problems = [];
  const workflow = join(root, ".github/workflows/auto-merge.yml");
  const guard = join(root, "bin/pr_guard.py");
  if (!existsSync(workflow)) {
    push(problems, "pr-contract", ".github/workflows/auto-merge.yml", "missing auto-merge workflow");
  } else {
    const text = readFileSync(workflow, "utf8");
    if (!text.includes("(feat|fix|docs|refactor|perf|test|build|ci|chore|revert)")) {
      push(problems, "pr-contract", ".github/workflows/auto-merge.yml", "missing conventional title check");
    }
    if (!text.includes("Why|What changed|Scope|Blast Radius|Verification")) {
      push(problems, "pr-contract", ".github/workflows/auto-merge.yml", "missing ordered body headings");
    }
  }
  if (!existsSync(guard)) {
    push(problems, "pr-contract", "bin/pr_guard.py", "missing local PR guard");
  }
  return problems;
}

export function checkWorkflowWiring(root) {
  return [
    ...checkRouterWiring(root),
    ...checkIntakeWiring(root),
    ...checkPolicyWiring(root),
    ...checkPrContract(root),
  ];
}

const CHECKS = [
  checkSkillStructure,
  checkAsciiProse,
  checkCommentDiscipline,
  checkAgentsContract,
  checkInstructionOwners,
  checkRelativeLinks,
  checkRouterWiring,
  checkIntakeWiring,
  checkPolicyWiring,
  checkPrContract,
];

function selfTests() {
  const tmp = mkdtempSync(join(tmpdir(), "harness-ratchets-"));
  try {
    mkdirSync(join(tmp, "skills/short"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/short/SKILL.md"),
      `---\nname: short\ndescription: valid\n---\n\n# Short\n`,
    );
    assert.deepEqual(checkSkillStructure(tmp), [], "a valid short skill must pass");

    mkdirSync(join(tmp, "skills/renamed"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/renamed/SKILL.md"),
      `---\nname: other\ndescription: mismatch\n---\n\n# Other\n`,
    );
    assert.ok(
      checkSkillStructure(tmp).some((problem) => problem.message.includes("must match the directory")),
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
    writeFileSync(join(tmp, "src/bad.js"), "const x = 1; // workaround for the retry loop\n");
    assert.ok(
      checkCommentDiscipline(tmp).some((problem) => problem.message.includes("workaround")),
      "an inline workaround comment must fail",
    );
    writeFileSync(join(tmp, "src/bad.js"), 'const s = "don\'t touch"; // workaround: do not remove\n');
    assert.ok(
      checkCommentDiscipline(tmp).some((problem) => problem.message.includes("workaround")),
      "an apostrophe inside a double-quoted string must not hide the comment",
    );
    writeFileSync(join(tmp, "src/bad.js"), "const x = 1;\n");
    writeFileSync(join(tmp, "src/url.js"), 'const url = "https://example.com";\n');
    assert.deepEqual(checkCommentDiscipline(tmp), [], "a URL inside a string is not a comment");
    writeFileSync(join(tmp, "src/ok.py"), "value = 'a # b'  # SPDX-License-Identifier: MIT\n");
    assert.deepEqual(checkCommentDiscipline(tmp), [], "a hash inside a string is not a comment");
    writeFileSync(join(tmp, "src/bad.js"), "const x = 1;\n/* workaround: do not remove */\n");
    assert.ok(
      checkCommentDiscipline(tmp).some((problem) => problem.line === 2),
      "a single-line block comment must be scanned",
    );
    writeFileSync(join(tmp, "src/bad.js"), "/*\n * workaround: do not remove\n */\nconst x = 1;\n");
    assert.ok(
      checkCommentDiscipline(tmp).some((problem) => problem.line === 2),
      "a multi-line block comment must be scanned",
    );
    writeFileSync(join(tmp, "src/bad.js"), "const x = 1;\n");

    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n");
    assert.deepEqual(checkAgentsContract(tmp), [], "a small enforced AGENTS.md must pass");
    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Task scale\n\nlong prose\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n");
    assert.ok(
      checkAgentsContract(tmp).some((problem) => problem.message.includes("routing belongs in skills/engineering-loop")),
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

    mkdirSync(join(tmp, "skills/engineering-loop/references/playbooks"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/engineering-loop/SKILL.md"),
      `# Router\n\n## Playbook router\n\n${PLAYBOOKS.map((name) => `| \`${name}\` | use |`).join("\n")}\n\nSee references/playbooks/<id>.md.\n\n## Fallback\n\nUse feature.\n`,
    );
    writeFileSync(
      join(tmp, "skills/engineering-loop/references/playbooks.md"),
      PLAYBOOKS.map((name) => `- [${name}](playbooks/${name}.md)`).join("\n"),
    );
    for (const name of PLAYBOOKS) {
      writeFileSync(
        join(tmp, "skills/engineering-loop/references/playbooks", `${name}.md`),
        "1. one\n2. two\n3. three\n",
      );
    }
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
    writeFileSync(join(tmp, "plugins/auto-intake.js"), `export const PLAYBOOK_IDS = ${JSON.stringify(PLAYBOOKS)};\nexport function routePrompt(text) { return text; }\n`);
    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n");
    mkdirSync(join(tmp, ".github/workflows"), { recursive: true });
    mkdirSync(join(tmp, "bin"), { recursive: true });
    writeFileSync(
      join(tmp, ".github/workflows/auto-merge.yml"),
      "(feat|fix|docs|refactor|perf|test|build|ci|chore|revert)\nWhy|What changed|Scope|Blast Radius|Verification\n",
    );
    writeFileSync(
      join(tmp, "bin/pr_guard.py"),
      "def body_problems(body):\n    return []\n",
    );
    assert.deepEqual(checkWorkflowWiring(tmp), [], "complete wiring must pass");

    writeFileSync(join(tmp, "skills/engineering-loop/references/playbooks/perf.md"), "1. one\n");
    assert.ok(
      checkWorkflowWiring(tmp).some((problem) => problem.message.includes("needs at least")),
      "a hollow playbook file must fail",
    );
    writeFileSync(
      join(tmp, "skills/engineering-loop/references/playbooks/perf.md"),
      "1. one\n2. two\n3. three\n",
    );

    writeFileSync(join(tmp, "plugins/auto-intake.js"), 'export const PLAYBOOK_IDS = ["bug-fix"];\nexport function routePrompt() {}\n');
    assert.ok(
      checkIntakeWiring(tmp).some((problem) => problem.message.includes("PLAYBOOK_IDS is missing")),
      "a playbook id list that drifts from the eight sections must fail",
    );
    writeFileSync(join(tmp, "plugins/auto-intake.js"), `export const PLAYBOOK_IDS = ${JSON.stringify(PLAYBOOKS)};\nexport function routePrompt(text) { return text; }\n`);
    writeFileSync(join(tmp, "commands/review.md"), "Jev review and independent verifier PASS.\n");
    assert.ok(
      checkPolicyWiring(tmp).some(
        (problem) =>
          problem.rule === "policy-wiring" &&
          problem.file === "commands/review.md",
      ),
      "agent-facing Jev and independent-verdict policy must fail",
    );
    writeFileSync(join(tmp, "commands/review.md"), "We achieve the goal with observed exits.\n");
    assert.deepEqual(
      checkPolicyWiring(tmp),
      [],
      "the substring jev inside an unrelated word must pass",
    );
    writeFileSync(join(tmp, "commands/review.md"), "A gate cannot certify its own weakening.\n");
    assert.ok(
      checkPolicyWiring(tmp).some((problem) =>
        problem.message.includes("gate cannot certify"),
      ),
      "the stale gate exception must fail",
    );
    writeFileSync(join(tmp, "commands/review.md"), "review\n");

    mkdirSync(join(tmp, "docs"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/README.md"),
      "| Skill | Use |\n|---|---|\n| `one` | valid |\n",
    );
    writeFileSync(join(tmp, "README.md"), "See [skills](skills/README.md).\n");
    writeFileSync(
      join(tmp, "docs/reference.md"),
      "See [skills](../skills/README.md).\n",
    );
    const agentsWithLink = "# Rules\n\nSee [skills](skills/README.md).\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n";
    writeFileSync(join(tmp, "AGENTS.md"), agentsWithLink);
    assert.deepEqual(checkInstructionOwners(tmp), [], "one owner and three links must pass");
    writeFileSync(
      join(tmp, "AGENTS.md"),
      "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n",
    );
    assert.ok(
      checkInstructionOwners(tmp).some((problem) =>
        problem.message.includes("must link"),
      ),
      "AGENTS.md without a skill-map link must fail",
    );
    writeFileSync(join(tmp, "AGENTS.md"), agentsWithLink);
    writeFileSync(join(tmp, "README.md"), "| Skill | Use |\n|---|---|\n| `two` | duplicate |\n");
    assert.ok(
      checkInstructionOwners(tmp).some((problem) =>
        problem.message.includes("one owner"),
      ),
      "a second skill table must fail",
    );
    writeFileSync(join(tmp, "README.md"), "See [skills](skills/README.md).\n");
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
