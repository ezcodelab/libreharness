// SPDX-License-Identifier: MIT
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  McpServer,
  fromJsonSchema,
} from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import { ROOT, ensureStateDirectory, statePath } from "./runtime.js";
import { TOOLS } from "./tools.js";

export function serverVersion() {
  return JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")).version;
}

export function createServer(options = {}) {
  const state = options.state ?? statePath(process.env.HARNESS_STATE);
  ensureStateDirectory(state);
  const server = new McpServer({
    name: "libreharness",
    version: options.version ?? serverVersion(),
  });
  for (const tool of TOOLS) {
    server.registerTool(
      tool.name,
      {
        description: tool.description,
        inputSchema: fromJsonSchema(tool.input),
      },
      async (input, context) => {
        try {
          const text = await tool.execute(input, {
            state,
            cwd: options.cwd ?? process.cwd(),
            signal: context.mcpReq.signal,
          });
          return { content: [{ type: "text", text }] };
        } catch (error) {
          return {
            content: [{ type: "text", text: error?.message ?? String(error) }],
            isError: true,
          };
        }
      },
    );
  }
  return server;
}

export async function main() {
  const server = createServer();
  await server.connect(new StdioServerTransport());
}
